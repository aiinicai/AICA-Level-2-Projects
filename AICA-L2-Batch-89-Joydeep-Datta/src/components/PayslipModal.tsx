import React, { useState, useEffect } from 'react';
import { X, Printer, Download, CheckCircle2, Shield, Loader2, FileText, Info } from 'lucide-react';
import { MonthlySalaryRecord, TaxConfig } from '../types/payroll';
import { amountToWordsIndian } from '../utils/numberToWords';
import { downloadPayslipPdf, getVectorPayslipBlobUrl } from '../utils/pdfPayslipGenerator';

interface PayslipModalProps {
  record: MonthlySalaryRecord | null;
  taxConfig: TaxConfig;
  onClose: () => void;
}

export const PayslipModal: React.FC<PayslipModalProps> = ({ record, taxConfig, onClose }) => {
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [printFeedback, setPrintFeedback] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'document' | 'print-view'>('document');
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (pdfBlobUrl) {
        URL.revokeObjectURL(pdfBlobUrl);
      }
    };
  }, [pdfBlobUrl]);

  if (!record) return null;

  const preparePdfBlob = () => {
    if (!pdfBlobUrl) {
      const url = getVectorPayslipBlobUrl(record);
      setPdfBlobUrl(url);
      return url;
    }
    return pdfBlobUrl;
  };

  const handlePrint = () => {
    setPrintFeedback('Preparing Print...');
    preparePdfBlob();
    setViewMode('print-view');

    // Attempt direct window.print() (works in direct browser tabs or when allow-modals is supported)
    try {
      window.print();
    } catch (e) {
      console.warn('Direct window.print() restricted in sandbox:', e);
    }

    setTimeout(() => {
      setPrintFeedback(null);
    }, 2000);
  };

  const handleDownloadPdf = async () => {
    setIsExportingPdf(true);
    try {
      await downloadPayslipPdf('printable-payslip', record);
    } catch (err) {
      console.error('Error generating PDF:', err);
    } finally {
      setIsExportingPdf(false);
    }
  };

  const netWords = amountToWordsIndian(record.netPay);

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 print:p-0 print:static print:bg-white print:overflow-visible">
      <div className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[92vh] print:max-h-none print:shadow-none print:border-none print:w-full print:rounded-none">
        {/* Modal Top Bar */}
        <div className="modal-top-bar px-6 py-3 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2 print:hidden">
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Payslip — {record.monthName} {record.year}
            </span>

            {/* View Mode Switcher */}
            <div className="flex items-center bg-slate-200/80 p-0.5 rounded-lg text-xs font-medium">
              <button
                type="button"
                onClick={() => setViewMode('document')}
                className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer flex items-center gap-1.5 ${
                  viewMode === 'document'
                    ? 'bg-white text-indigo-700 shadow-xs font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <FileText className="h-3.5 w-3.5" />
                Document View
              </button>
              <button
                type="button"
                onClick={() => {
                  preparePdfBlob();
                  setViewMode('print-view');
                }}
                className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer flex items-center gap-1.5 ${
                  viewMode === 'print-view'
                    ? 'bg-white text-indigo-700 shadow-xs font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Printer className="h-3.5 w-3.5" />
                Print-Ready Viewer
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleDownloadPdf}
              disabled={isExportingPdf}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 rounded-lg transition-colors shadow-xs cursor-pointer"
              title="Save PDF directly to your device"
            >
              {isExportingPdf ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Download className="h-3.5 w-3.5" />
                  Download PDF
                </>
              )}
            </button>
            <button
              type="button"
              onClick={handlePrint}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors border border-slate-300 cursor-pointer"
              title="Open print view with direct printer controls"
            >
              <Printer className="h-3.5 w-3.5 text-slate-600" />
              <span>{printFeedback || 'Print'}</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* View Mode 1: Print-Ready Embedded PDF Viewer */}
        {viewMode === 'print-view' && (
          <div className="p-4 sm:p-6 overflow-y-auto space-y-4 flex-1 bg-slate-100">
            {/* Browser Sandboxing Explanation Box */}
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 flex items-start gap-3 text-xs text-amber-900">
              <Info className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold">Why system print popups are restricted in embedded previews:</p>
                <p className="text-amber-800 leading-relaxed">
                  Web browsers (Chrome, Edge, Safari) prohibit modal dialogs (like <code className="bg-amber-100 px-1 py-0.5 rounded font-mono text-[11px]">window.print()</code>) inside sandboxed preview iframes unless the host sets the <code className="bg-amber-100 px-1 py-0.5 rounded font-mono text-[11px]">allow-modals</code> flag.
                </p>
                <p className="text-amber-800 leading-relaxed">
                  You can print with zero restrictions by either:
                  <strong className="block mt-1">1. Using the Print icon on the built-in PDF viewer toolbar below</strong>
                  <strong>2. Clicking "Download PDF" to print from any desktop PDF reader</strong>
                  <strong>3. Opening the app in a standalone tab via the Shared App URL</strong>
                </p>
              </div>
            </div>

            {/* Embedded PDF Canvas with Built-In Print Controls */}
            {pdfBlobUrl ? (
              <div className="bg-white rounded-xl shadow-xs border border-slate-300 overflow-hidden">
                <iframe
                  src={`${pdfBlobUrl}#toolbar=1&navpanes=0`}
                  title="Print Ready Salary Payslip"
                  className="w-full h-[620px] border-0"
                />
              </div>
            ) : (
              <div className="flex items-center justify-center p-12 bg-white rounded-xl border border-slate-200">
                <Loader2 className="h-6 w-6 animate-spin text-indigo-600 mr-2" />
                <span className="text-sm text-slate-600 font-medium">Rendering print-ready PDF...</span>
              </div>
            )}
          </div>
        )}

        {/* View Mode 2: Standard HTML Document Body */}
        <div
          id="printable-payslip"
          className={`p-8 overflow-y-auto space-y-6 text-slate-800 text-xs print:p-4 print:overflow-visible print:text-black ${
            viewMode === 'print-view' ? 'hidden print:block' : 'block'
          }`}
        >
          {/* Company & Payslip Header */}
          <div className="border-b-2 border-slate-900 pb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <h2 className="text-xl font-black text-slate-900 tracking-tight">ACME ENTERPRISES INDIA PVT LTD</h2>
              <p className="text-xs text-slate-500">Corporate Payroll & TDS Disbursement Division</p>
            </div>
            <div className="text-right">
              <span className="text-sm font-bold text-slate-900 uppercase">
                Salary Slip: {record.monthName} {record.year}
              </span>
              <p className="text-[10px] text-slate-400 font-mono">
                Generated per Indian Income Tax Rules u/s 192
              </p>
            </div>
          </div>

          {/* Employee Demographic & Bank Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div>
              <span className="text-[10px] text-slate-400 font-medium block">Employee Code</span>
              <strong className="font-mono text-slate-900 text-xs">{record.employeeCode}</strong>
            </div>

            <div>
              <span className="text-[10px] text-slate-400 font-medium block">Employee Name</span>
              <strong className="text-slate-900 text-xs">{record.employeeName}</strong>
            </div>

            <div>
              <span className="text-[10px] text-slate-400 font-medium block">Designation</span>
              <span className="text-slate-800 text-xs">{record.designation}</span>
            </div>

            <div>
              <span className="text-[10px] text-slate-400 font-medium block">Department</span>
              <span className="text-slate-800 text-xs">{record.department}</span>
            </div>

            <div>
              <span className="text-[10px] text-slate-400 font-medium block">PAN</span>
              <strong className="font-mono text-slate-900 text-xs">{record.pan}</strong>
            </div>

            <div>
              <span className="text-[10px] text-slate-400 font-medium block">Tax Regime</span>
              <span className="font-semibold text-indigo-700 text-xs">
                {record.regimeApplied} Regime
              </span>
            </div>

            <div>
              <span className="text-[10px] text-slate-400 font-medium block">Bank Account No</span>
              <span className="font-mono text-slate-800 text-xs">{record.bankAccountNo}</span>
            </div>

            <div>
              <span className="text-[10px] text-slate-400 font-medium block">Bank & IFSC</span>
              <span className="text-slate-800 text-xs">
                {record.bankName} ({record.ifsc})
              </span>
            </div>
          </div>

          {/* Attendance Summary */}
          <div className="flex items-center justify-between px-4 py-2 bg-slate-100/60 rounded-lg text-xs font-mono">
            <span>
              Total Days in Month: <strong>{record.totalDaysInMonth}</strong>
            </span>
            <span>
              Payable Days: <strong>{record.payableDays}</strong>
            </span>
            <span>
              LOP (Loss of Pay): <strong>{record.lopDays}</strong>
            </span>
            <span>
              Proration Factor: <strong>{(record.prorationFactor * 100).toFixed(1)}%</strong>
            </span>
          </div>

          {/* Side-by-Side Earnings & Deductions Tables */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Earnings */}
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <div className="bg-slate-100 px-3 py-2 font-bold text-slate-800 border-b border-slate-200">
                Earnings
              </div>
              <table className="w-full text-left font-mono text-xs divide-y divide-slate-100">
                <tbody>
                  <tr>
                    <td className="py-1.5 px-3">Basic Salary</td>
                    <td className="py-1.5 px-3 text-right">₹{record.basicEarned.toLocaleString('en-IN')}</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 px-3">House Rent Allowance (HRA)</td>
                    <td className="py-1.5 px-3 text-right">₹{record.hraEarned.toLocaleString('en-IN')}</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 px-3">Conveyance Allowance</td>
                    <td className="py-1.5 px-3 text-right">₹{record.conveyanceEarned.toLocaleString('en-IN')}</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 px-3">Special Allowance</td>
                    <td className="py-1.5 px-3 text-right">
                      ₹{record.specialAllowanceEarned.toLocaleString('en-IN')}
                    </td>
                  </tr>
                  {record.ceaEarned > 0 && (
                    <tr>
                      <td className="py-1.5 px-3">Children Education Allw</td>
                      <td className="py-1.5 px-3 text-right">₹{record.ceaEarned.toLocaleString('en-IN')}</td>
                    </tr>
                  )}
                  {record.ltaEarned > 0 && (
                    <tr>
                      <td className="py-1.5 px-3">LTA Monthly</td>
                      <td className="py-1.5 px-3 text-right">₹{record.ltaEarned.toLocaleString('en-IN')}</td>
                    </tr>
                  )}
                  {record.variablePayEarned > 0 && (
                    <tr>
                      <td className="py-1.5 px-3">Variable Pay</td>
                      <td className="py-1.5 px-3 text-right">
                        ₹{record.variablePayEarned.toLocaleString('en-IN')}
                      </td>
                    </tr>
                  )}
                  {record.joiningBonusEarned > 0 && (
                    <tr>
                      <td className="py-1.5 px-3">Joining Bonus</td>
                      <td className="py-1.5 px-3 text-right">
                        ₹{record.joiningBonusEarned.toLocaleString('en-IN')}
                      </td>
                    </tr>
                  )}
                </tbody>
                <tfoot className="bg-slate-50 font-bold border-t border-slate-200">
                  <tr>
                    <td className="py-2 px-3 text-slate-900">Total Gross Earned</td>
                    <td className="py-2 px-3 text-right text-slate-900">
                      ₹{record.grossEarned.toLocaleString('en-IN')}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>

            {/* Deductions */}
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <div className="bg-slate-100 px-3 py-2 font-bold text-slate-800 border-b border-slate-200">
                Deductions
              </div>
              <table className="w-full text-left font-mono text-xs divide-y divide-slate-100">
                <tbody>
                  <tr>
                    <td className="py-1.5 px-3">Provident Fund (EPF 12%)</td>
                    <td className="py-1.5 px-3 text-right">₹{record.employeePf.toLocaleString('en-IN')}</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 px-3">ESI Contribution</td>
                    <td className="py-1.5 px-3 text-right">₹{record.esi.toLocaleString('en-IN')}</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 px-3">Professional Tax</td>
                    <td className="py-1.5 px-3 text-right">₹0 (Exempt)</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 px-3 font-semibold text-amber-800">
                      Income Tax (Monthly TDS)
                    </td>
                    <td className="py-1.5 px-3 text-right font-semibold text-amber-800">
                      ₹{record.tdsDeducted.toLocaleString('en-IN')}
                    </td>
                  </tr>
                  {record.otherDeductions > 0 && (
                    <tr>
                      <td className="py-1.5 px-3">Other Deductions</td>
                      <td className="py-1.5 px-3 text-right">
                        ₹{record.otherDeductions.toLocaleString('en-IN')}
                      </td>
                    </tr>
                  )}
                </tbody>
                <tfoot className="bg-slate-50 font-bold border-t border-slate-200">
                  <tr>
                    <td className="py-2 px-3 text-slate-900">Total Deductions</td>
                    <td className="py-2 px-3 text-right text-slate-900">
                      ₹{record.totalDeductions.toLocaleString('en-IN')}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          {/* Net Pay Highlight Card */}
          <div className="bg-indigo-50 border-2 border-indigo-200 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <span className="text-[11px] font-bold text-indigo-700 uppercase tracking-wider">
                Net Take-Home Pay
              </span>
              <p className="text-xs text-slate-700 mt-0.5 italic">{netWords}</p>
            </div>
            <div className="text-right">
              <span className="text-2xl font-black text-indigo-950 font-mono">
                ₹{record.netPay.toLocaleString('en-IN')}
              </span>
            </div>
          </div>

          {/* Statutory Employer Contributions Summary */}
          <div className="border border-slate-200 rounded-lg p-3 bg-slate-50/50 text-[11px] space-y-1">
            <span className="font-bold text-slate-700 block">Employer Contributions (Cost to Company):</span>
            <div className="flex flex-wrap gap-4 font-mono text-slate-600">
              <span>Employer PF: ₹{record.employerPf.toLocaleString('en-IN')}</span>
              <span>Employer NPS: ₹{record.employerNps.toLocaleString('en-IN')}</span>
              <span>Gratuity Provision: ₹{record.gratuityProvision.toLocaleString('en-IN')}</span>
              <span>
                Total Employer Cost: <strong>₹{record.totalEmployerCost.toLocaleString('en-IN')}</strong>
              </span>
            </div>
          </div>

          {/* Footer & Compliance Stamp */}
          <div className="pt-4 border-t border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between text-[10px] text-slate-400 font-mono gap-2">
            <span>This is a computer-generated salary slip. No physical signature required.</span>
            <span>
              TaxConfig: FY{taxConfig.financialYear} | sha256:{taxConfig.approval.contentSha256.substring(0, 12)}...
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
