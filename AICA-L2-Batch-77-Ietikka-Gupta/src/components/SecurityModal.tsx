import React from 'react';
import { X, ShieldCheck, Lock, EyeOff, Server, CheckCircle2 } from 'lucide-react';

interface SecurityModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SecurityModal: React.FC<SecurityModalProps> = ({
  isOpen,
  onClose,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Modal Header */}
        <div className="p-4 sm:p-5 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <h3 className="text-base font-bold text-slate-50">
              Audit Data Security & Confidentiality Architecture
            </h3>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-4 overflow-y-auto text-xs text-slate-700 leading-relaxed">
          
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 flex items-start gap-3">
            <div className="p-2 bg-emerald-100 rounded-lg text-emerald-800 shrink-0">
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-bold text-emerald-950 text-xs">Zero Persistent Document Storage</h4>
              <p className="text-emerald-800 text-[11.5px] mt-0.5">
                All uploaded ESI and PF challan PDFs are handled strictly in transient server memory (RAM) during digitization. No client PDFs or challan images are ever saved to disk or permanent databases.
              </p>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-start gap-2.5 p-3 rounded-xl border border-slate-200 bg-slate-50">
              <EyeOff className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-900 block font-semibold">ICAI Confidentiality Compliance</strong>
                <span className="text-slate-600 text-[11.5px]">
                  Built in alignment with the Institute of Chartered Accountants of India (ICAI) Code of Ethics regarding client confidentiality and sensitive payroll/financial data privacy.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2.5 p-3 rounded-xl border border-slate-200 bg-slate-50">
              <Server className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-900 block font-semibold">Client-Side Export Processing</strong>
                <span className="text-slate-600 text-[11.5px]">
                  Excel (.xlsx) and PDF report generation occur directly within your browser session using standard cryptographic sandboxing.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2.5 p-3 rounded-xl border border-slate-200 bg-slate-50">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-900 block font-semibold">Session Isolation</strong>
                <span className="text-slate-600 text-[11.5px]">
                  Every audit session is isolated. Clicking "Clear All" or refreshing completely purges all working records from your local session.
                </span>
              </div>
            </div>
          </div>

        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <span className="text-[11px] text-slate-500 font-medium">
            Designed for professional Chartered Accountancy practices
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold transition cursor-pointer"
          >
            Acknowledge & Close
          </button>
        </div>

      </div>
    </div>
  );
};
