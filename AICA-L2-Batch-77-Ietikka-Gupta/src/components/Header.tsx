import React from 'react';
import { 
  FileSpreadsheet, 
  FileText, 
  ShieldCheck, 
  BookOpen, 
  Building2,
  Plus,
  Sparkles,
  Lock
} from 'lucide-react';
import { AssesseeDetails } from '../types';

interface HeaderProps {
  assessee: AssesseeDetails;
  onOpenAssesseeModal: () => void;
  onOpenKnowledgeModal: () => void;
  onOpenSecurityModal: () => void;
  onOpenAddModal: () => void;
  onExportExcel: () => void;
  onExportPdf: () => void;
  recordCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  assessee,
  onOpenAssesseeModal,
  onOpenKnowledgeModal,
  onOpenSecurityModal,
  onOpenAddModal,
  onExportExcel,
  onExportPdf,
  recordCount,
}) => {
  return (
    <header className="bg-white border-b border-slate-200/80 sticky top-0 z-40 shadow-xs backdrop-blur-md bg-white/95">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between py-4 gap-4">
          
          {/* Brand & Creator Attribution - Bento Themed */}
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 rounded-2xl bg-indigo-600 flex items-center justify-center text-white font-black text-lg shadow-md shadow-indigo-200 ring-4 ring-indigo-50">
              3CD
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
                  AuditPulse AI
                </h1>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-[11px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-100">
                  Certified System
                </span>
                <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                  Clause 20(b)
                </span>
              </div>
              <p className="text-xs text-slate-500 flex items-center gap-2 mt-0.5">
                <span>ESI & PF Challan Digitalization Dashboard</span>
                <span className="text-slate-300">•</span>
                <span className="text-slate-600 font-medium">
                  Created by <strong className="text-slate-900 font-bold">{assessee.auditorName}</strong> (Chartered Accountant)
                </span>
              </p>
            </div>
          </div>

          {/* Quick Client & Action Controls */}
          <div className="flex flex-wrap items-center gap-2.5">
            
            {/* Assessee Info Bento Pill */}
            <button
              onClick={onOpenAssesseeModal}
              id="assessee-config-btn"
              className="inline-flex items-center gap-2 px-3.5 py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl text-xs font-medium transition cursor-pointer shadow-2xs"
              title="Edit Client & Auditor Details"
            >
              <Building2 className="w-4 h-4 text-indigo-600" />
              <div className="text-left">
                <span className="block truncate max-w-[140px] font-bold text-slate-800">{assessee.name}</span>
                <span className="text-[10px] text-slate-500 font-mono">AY {assessee.assessmentYear} | {assessee.pan}</span>
              </div>
            </button>

            {/* Knowledge & Security buttons */}
            <button
              onClick={onOpenKnowledgeModal}
              id="tax-law-help-btn"
              className="p-2.5 text-slate-600 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 rounded-xl border border-slate-200 text-xs flex items-center gap-1.5 transition cursor-pointer shadow-2xs"
              title="Tax Audit & Legal Provisions Reference"
            >
              <BookOpen className="w-4 h-4 text-amber-600" />
              <span className="hidden sm:inline font-semibold">36(1)(va) Law</span>
            </button>

            <button
              onClick={onOpenSecurityModal}
              id="security-info-btn"
              className="p-2.5 text-emerald-700 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100 rounded-xl border border-emerald-200 text-xs flex items-center gap-1.5 transition cursor-pointer shadow-2xs"
              title="Audit Confidentiality & Security Guarantee"
            >
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span className="hidden sm:inline font-semibold">100% Secure</span>
            </button>

            {/* Add Manual Row Button */}
            <button
              onClick={onOpenAddModal}
              id="add-manual-challan-btn"
              className="inline-flex items-center gap-1.5 px-3.5 py-2.5 bg-white hover:bg-slate-50 text-slate-800 border border-slate-200 rounded-xl text-xs font-semibold transition cursor-pointer shadow-2xs"
            >
              <Plus className="w-4 h-4 text-indigo-600" />
              <span>Add Entry</span>
            </button>

            {/* Export Buttons */}
            <div className="flex items-center gap-2 pl-1 border-l border-slate-200">
              <button
                onClick={onExportExcel}
                disabled={recordCount === 0}
                id="export-excel-btn"
                className={`inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl text-xs font-bold shadow-sm transition ${
                  recordCount === 0 
                    ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
                    : 'bg-slate-900 hover:bg-slate-800 text-white cursor-pointer active:scale-95'
                }`}
                title="Download Form 3CD Clause 20(b) Excel Workbook"
              >
                <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
                <span>Excel (.xlsx)</span>
              </button>

              <button
                onClick={onExportPdf}
                disabled={recordCount === 0}
                id="export-pdf-btn"
                className={`inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl text-xs font-bold shadow-md shadow-indigo-100 transition ${
                  recordCount === 0 
                    ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
                    : 'bg-indigo-600 hover:bg-indigo-700 text-white cursor-pointer active:scale-95'
                }`}
                title="Download Formal Tax Audit Annexure PDF"
              >
                <FileText className="w-4 h-4 text-white" />
                <span>Audit PDF</span>
              </button>
            </div>

          </div>

        </div>
      </div>
    </header>
  );
};
