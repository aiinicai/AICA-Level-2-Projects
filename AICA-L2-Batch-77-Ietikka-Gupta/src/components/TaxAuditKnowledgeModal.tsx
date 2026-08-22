import React from 'react';
import { X, BookOpen, Scale, AlertTriangle, CheckCircle2, FileText, Landmark } from 'lucide-react';

interface TaxAuditKnowledgeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const TaxAuditKnowledgeModal: React.FC<TaxAuditKnowledgeModalProps> = ({
  isOpen,
  onClose,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Modal Header */}
        <div className="p-4 sm:p-5 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Scale className="w-5 h-5 text-amber-400" />
            <h3 className="text-base font-bold text-slate-50">
              Tax Audit Legal Framework: Section 36(1)(va) & Form 3CD Clause 20(b)
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
          
          {/* Section 1: Crucial Distinction */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5">
            <h4 className="font-bold text-amber-950 flex items-center gap-1.5 text-xs mb-1.5">
              <AlertTriangle className="w-4 h-4 text-amber-700" />
              Critical Statutory Distinction: Employee Contribution vs Employer Contribution
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2 text-[11.5px]">
              <div className="bg-white p-2.5 rounded-lg border border-amber-100">
                <span className="font-bold text-slate-900 block mb-0.5">Employee Share [Sec 36(1)(va)]</span>
                <p className="text-slate-600">
                  Deduction allowed <strong>ONLY</strong> if deposited on or before the 15th of the succeeding month (Statutory Due Date). <strong>Section 43B does NOT apply.</strong> Delay of even 1 day leads to permanent disallowance.
                </p>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-amber-100">
                <span className="font-bold text-slate-900 block mb-0.5">Employer Share [Sec 43B(b)]</span>
                <p className="text-slate-600">
                  Allowable as deduction if paid <strong>on or before the due date of filing ITR</strong> under Section 139(1). Reported separately under Clause 26 of Form 3CD.
                </p>
              </div>
            </div>
          </div>

          {/* Section 2: Supreme Court Landmark Decision */}
          <div className="border border-slate-200 rounded-xl p-3.5 bg-slate-50">
            <h4 className="font-bold text-slate-900 flex items-center gap-1.5 text-xs mb-1">
              <Landmark className="w-4 h-4 text-sky-700" />
              Landmark Supreme Court Ruling: Checkmate Services P. Ltd vs CIT (2022)
            </h4>
            <p className="text-slate-600 text-[11.5px] mt-1">
              The Hon’ble Supreme Court of India in <em>Checkmate Services Pvt. Ltd. v. CIT [2022] 448 ITR 518 (SC)</em> definitively held that employee contribution received by the employer is deemed income under Section 2(24)(x). It is only deductible if paid within the due date prescribed in the respective PF/ESI schemes. Section 43B cannot rescue delayed deposits of employee contributions.
            </p>
          </div>

          {/* Section 3: Statutory Due Dates */}
          <div className="border border-slate-200 rounded-xl p-3.5 space-y-2">
            <h4 className="font-bold text-slate-900 flex items-center gap-1.5 text-xs">
              <BookOpen className="w-4 h-4 text-indigo-700" />
              Statutory Due Date Determination Rules in India
            </h4>
            
            <ul className="list-disc pl-4 space-y-1.5 text-slate-600 text-[11.5px]">
              <li>
                <strong>Employees' Provident Fund (EPFO):</strong> Paragraph 38 of Employees' Provident Funds Scheme, 1952 specifies that the payment must be made within 15 days of the close of the month (e.g. for April wage month, due date is 15th May).
              </li>
              <li>
                <strong>Employees' State Insurance (ESIC):</strong> Regulation 31 of ESI (General) Regulations, 1950 specifies payment within 15 days of the last day of the calendar month in which contributions fall due.
              </li>
              <li>
                <strong>Grace Period:</strong> Note that EPFO previously had a 5-day grace period, which was <strong>withdrawn effective February 2016</strong>. Currently, 15th is the strict hard deadline.
              </li>
            </ul>
          </div>

          {/* Section 4: Form 3CD Reporting */}
          <div className="border border-slate-200 rounded-xl p-3.5 bg-sky-50/50">
            <h4 className="font-bold text-slate-900 flex items-center gap-1.5 text-xs mb-1">
              <FileText className="w-4 h-4 text-sky-700" />
              Clause 20(b) Requirements in Form 3CD
            </h4>
            <p className="text-slate-600 text-[11.5px]">
              Tax Auditors are required to report every payment in the 8-column format. If the actual date of payment exceeds the statutory due date, the employee contribution amount must be stated in column 7 ("Amount not paid to employee's account by due date") and added back to taxable profits in the computation of total income.
            </p>
          </div>

        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <span className="text-[11px] text-slate-500 font-medium">
            Compiled for Indian Tax Audit Practices by CA Ietikka Gupta
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold transition cursor-pointer"
          >
            Close Reference
          </button>
        </div>

      </div>
    </div>
  );
};
