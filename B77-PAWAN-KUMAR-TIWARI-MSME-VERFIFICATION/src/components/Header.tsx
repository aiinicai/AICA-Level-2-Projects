import React, { useState } from 'react';
import {
  Menu,
  Bell,
  Calendar,
  Download,
  Plus,
  RotateCcw,
  FileSpreadsheet,
  AlertTriangle,
  ChevronDown,
  Shield,
  Upload,
  FileText,
  Sparkles,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { ExcelUploadModal } from './Common/ExcelUploadModal';
import { ExceptionAlertsModal } from './Common/ExceptionAlertsModal';
import { InvoiceDocUploadModal } from './Invoices/InvoiceDocUploadModal';
import { downloadInvoiceExcelTemplate } from '../utils/excelService';

interface HeaderProps {
  onToggleMobileSidebar: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleMobileSidebar }) => {
  const {
    activeTab,
    selectedFinancialYear,
    setSelectedFinancialYear,
    asOfDate,
    setAsOfDate,
    exceptionAlerts,
    resetToDemoData,
    currentUserRole,
  } = useApp();

  const [isExcelModalOpen, setIsExcelModalOpen] = useState(false);
  const [excelModalType, setExcelModalType] = useState<'invoices' | 'vendors'>('invoices');
  const [isDocUploadModalOpen, setIsDocUploadModalOpen] = useState(false);
  const [isAlertsModalOpen, setIsAlertsModalOpen] = useState(false);

  const getTitle = () => {
    switch (activeTab) {
      case 'dashboard':
        return 'Management Dashboard';
      case 'vendors':
        return 'MSME Vendor Master';
      case 'verification':
        return 'Udyam Verification Portal';
      case 'invoices':
        return 'Invoice & Statutory Due Register';
      case 'payments':
        return 'Payment & Tranche Register';
      case 'calculator':
        return 'Section 16 Interest Calculator';
      case 'ageing':
        return 'Statutory Ageing & Delay Matrix';
      case 'reports':
        return 'Compliance Reports & Form MSME-1';
      case 'masters':
        return 'Master Rules & RBI Rates';
      case 'audit':
        return 'Immutable Statutory Audit Trail';
      default:
        return 'MSME Compliance Portal';
    }
  };

  const highSeverityAlertCount = exceptionAlerts.filter((a) => a.severity === 'HIGH').length;

  const handleDownloadTemplate = () => {
    downloadInvoiceExcelTemplate();
  };

  return (
    <>
      <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-6 lg:px-8 flex items-center justify-between shrink-0 sticky top-0 z-30 shadow-xs">
        {/* Left Side: Mobile Menu Button + View Title */}
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleMobileSidebar}
            className="lg:hidden p-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 cursor-pointer"
            title="Toggle Navigation Menu"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-base sm:text-lg font-bold text-slate-800 tracking-tight leading-tight">
              {getTitle()}
            </h1>
            <div className="text-[10px] text-slate-400 font-medium hidden sm:flex items-center gap-1.5">
              <span>MSMED Act 2006 & Section 43B(h)</span>
              <span>•</span>
              <span className="text-blue-600 font-bold uppercase tracking-wider">Know. Calculate. Comply.</span>
            </div>
          </div>
        </div>

        {/* Right Side Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Financial Year Selector */}
          <div className="hidden xl:flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-2.5 py-1.5 rounded-lg text-xs">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">FY</span>
            <select
              value={selectedFinancialYear}
              onChange={(e) => setSelectedFinancialYear(e.target.value)}
              className="bg-transparent text-xs font-semibold text-slate-700 focus:outline-hidden cursor-pointer"
            >
              <option value="All">All Years</option>
              <option value="2026-27">2026-27 (Current)</option>
              <option value="2025-26">2025-26</option>
              <option value="2024-25">2024-25</option>
            </select>
          </div>

          {/* As-of Date Selector */}
          <div className="hidden md:flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-2.5 py-1.5 rounded-lg text-xs">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider hidden lg:inline">As-of</span>
            <input
              type="date"
              value={asOfDate}
              onChange={(e) => setAsOfDate(e.target.value)}
              className="bg-transparent text-xs font-semibold text-slate-800 focus:outline-hidden cursor-pointer w-28 sm:w-auto"
              title="Statutory Cutoff Date"
            />
          </div>

          {/* Exception Alerts Bell */}
          <button
            onClick={() => setIsAlertsModalOpen(true)}
            className="relative p-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-600 hover:text-slate-900 border border-slate-200 transition-colors cursor-pointer"
            title="View Critical Exception Alerts"
          >
            <Bell className="w-4 h-4" />
            {exceptionAlerts.length > 0 && (
              <span
                className={`absolute -top-1 -right-1 px-1.5 py-0.2 rounded-full text-[9px] font-extrabold text-white flex items-center justify-center ${
                  highSeverityAlertCount > 0 ? 'bg-red-600 animate-pulse' : 'bg-amber-500'
                }`}
              >
                {exceptionAlerts.length}
              </span>
            )}
          </button>

          {/* Excel Ingest Button */}
          <button
            onClick={() => {
              setExcelModalType('invoices');
              setIsExcelModalOpen(true);
            }}
            className="bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg text-xs font-semibold border border-slate-300 hidden sm:flex items-center gap-1.5 transition-all cursor-pointer"
            title="Import Invoices via Excel / CSV Spreadsheet"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-700" />
            <span className="hidden lg:inline">Import Excel</span>
          </button>

          {/* Upload PDF/JPEG Invoices Trigger (Primary) */}
          <button
            onClick={() => setIsDocUploadModalOpen(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-3.5 sm:px-4 py-1.5 rounded-lg text-xs font-bold transition-all shadow-xs flex items-center gap-1.5 cursor-pointer"
            title="Upload Invoices in PDF and JPEG with AI OCR Extraction"
          >
            <Upload className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Upload PDF / JPEG</span>
            <span className="sm:hidden">Upload</span>
            <span className="hidden md:inline-flex px-1.5 py-0.2 bg-blue-500 text-white rounded text-[9px] font-extrabold items-center gap-0.5">
              <Sparkles className="w-2.5 h-2.5" /> AI
            </span>
          </button>
        </div>
      </header>

      {/* Auditor Read-Only Notice Bar */}
      {currentUserRole === 'Auditor' && (
        <div className="bg-amber-50 border-b border-amber-200 px-6 py-1.5 text-center text-xs text-amber-800 flex items-center justify-center gap-1.5">
          <Shield className="w-3.5 h-3.5 text-amber-600" />
          <span>
            <strong>Auditor Read-Only Inspection Mode:</strong> Live statutory calculation schedules, notes to accounts, and audit log inspection active.
          </span>
        </div>
      )}

      {/* Modals */}
      <ExcelUploadModal
        isOpen={isExcelModalOpen}
        onClose={() => setIsExcelModalOpen(false)}
        type={excelModalType}
      />
      <InvoiceDocUploadModal
        isOpen={isDocUploadModalOpen}
        onClose={() => setIsDocUploadModalOpen(false)}
      />
      <ExceptionAlertsModal
        isOpen={isAlertsModalOpen}
        onClose={() => setIsAlertsModalOpen(false)}
      />
    </>
  );
};
