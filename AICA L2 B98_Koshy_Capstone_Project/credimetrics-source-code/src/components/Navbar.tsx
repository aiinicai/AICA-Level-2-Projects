import React from 'react';
import { 
  Building2, 
  ShieldCheck, 
  Download, 
  UploadCloud, 
  Plus, 
  History, 
  ChevronDown, 
  CheckCircle2, 
  AlertTriangle,
  UserCheck,
  FileSpreadsheet
} from 'lucide-react';
import { Company, User, UserRole } from '../types/financial';

interface NavbarProps {
  companies: Company[];
  selectedCompany: Company;
  onSelectCompany: (company: Company) => void;
  currentUser: User;
  onSwitchUser: (user: User) => void;
  availableUsers: User[];
  onOpenUpload: () => void;
  onOpenNewCompany: () => void;
  onOpenReportModal: () => void;
  onOpenAuditLogs: () => void;
  onQuickDownloadPdf: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  companies,
  selectedCompany,
  onSelectCompany,
  currentUser,
  onSwitchUser,
  availableUsers,
  onOpenUpload,
  onOpenNewCompany,
  onOpenReportModal,
  onOpenAuditLogs,
  onQuickDownloadPdf,
}) => {
  const [showCompanyMenu, setShowCompanyMenu] = React.useState(false);
  const [showUserMenu, setShowUserMenu] = React.useState(false);

  const getRoleBadgeColor = (role: UserRole) => {
    switch (role) {
      case 'Admin': return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'CA': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'Bank Officer': return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'Loan Consultant': return 'bg-amber-100 text-amber-800 border-amber-200';
      default: return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  return (
    <header className="sticky top-0 z-40 bg-slate-900 border-b border-slate-800 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Brand Logo & Name */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <ShieldCheck className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-lg tracking-tight text-white">CrediMetrics</span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-400/30">
                  Credit Intelligence
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">Financial Ratio Analysis &amp; Underwriting Engine</p>
            </div>
          </div>

          {/* Active Company Selector */}
          <div className="relative">
            <button
              onClick={() => {
                setShowCompanyMenu(!showCompanyMenu);
                setShowUserMenu(false);
              }}
              className="flex items-center space-x-2.5 bg-slate-800 hover:bg-slate-750 px-3.5 py-2 rounded-lg border border-slate-700 transition text-left"
              title="Switch Target Company"
            >
              <Building2 className="w-4 h-4 text-cyan-400 shrink-0" />
              <div className="max-w-[180px] md:max-w-[240px] truncate">
                <div className="text-xs text-slate-400 leading-none mb-0.5">Active Borrower</div>
                <div className="text-sm font-semibold text-white truncate">{selectedCompany.companyName}</div>
              </div>
              <ChevronDown className="w-4 h-4 text-slate-400" />
            </button>

            {showCompanyMenu && (
              <div className="absolute left-0 mt-2 w-80 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl py-2 z-50">
                <div className="px-3 py-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800 flex justify-between items-center">
                  <span>Select Borrower Entity</span>
                  <button 
                    onClick={() => {
                      setShowCompanyMenu(false);
                      onOpenNewCompany();
                    }}
                    className="text-cyan-400 hover:text-cyan-300 text-xs flex items-center gap-1 font-medium lowercase"
                  >
                    <Plus className="w-3 h-3" /> new company
                  </button>
                </div>
                <div className="max-h-72 overflow-y-auto py-1">
                  {companies.map(comp => (
                    <button
                      key={comp.id}
                      onClick={() => {
                        onSelectCompany(comp);
                        setShowCompanyMenu(false);
                      }}
                      className={`w-full text-left px-3.5 py-2.5 hover:bg-slate-800 transition flex items-start justify-between ${
                        comp.id === selectedCompany.id ? 'bg-slate-800/80 border-l-4 border-cyan-400' : ''
                      }`}
                    >
                      <div className="truncate pr-2">
                        <div className="text-sm font-medium text-slate-100 truncate">{comp.companyName}</div>
                        <div className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                          <span>{comp.industry}</span>
                          <span>•</span>
                          <span>INR {comp.annualTurnover} Cr</span>
                        </div>
                      </div>
                      {comp.id === selectedCompany.id && (
                        <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons & Persona Switcher */}
          <div className="flex items-center space-x-2 sm:space-x-3">
            {/* Upload Financials Button */}
            <button
              onClick={onOpenUpload}
              className="flex items-center space-x-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white px-3 py-2 rounded-lg text-xs font-medium border border-slate-700 transition"
              title="Upload Financials (Excel/CSV/Manual)"
            >
              <UploadCloud className="w-4 h-4 text-blue-400" />
              <span className="hidden md:inline">Upload Financials</span>
            </button>

            {/* Download Hub / Report Center */}
            <button
              onClick={onOpenReportModal}
              className="flex items-center space-x-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-3.5 py-2 rounded-lg text-xs font-semibold shadow-md shadow-blue-600/30 transition"
              title="Download Appraisal Report, Models & Templates"
            >
              <Download className="w-4 h-4" />
              <span>Download Report</span>
            </button>

            {/* Direct Project Code Zip Download */}
            <a
              href="/credimetrics-source-code.zip"
              download="credimetrics-credit-assessment-tool.zip"
              className="flex items-center space-x-1.5 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 hover:text-white px-3 py-2 rounded-lg text-xs font-bold border border-cyan-500/40 transition shadow-sm"
              title="Download Complete Source Code to Run Locally (.ZIP)"
            >
              <Download className="w-4 h-4 text-cyan-400" />
              <span className="hidden sm:inline">Source Code (.ZIP)</span>
            </a>

            {/* Audit Logs button */}
            <button
              onClick={onOpenAuditLogs}
              className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
              title="View Audit Trail & System Logs"
            >
              <History className="w-4 h-4" />
            </button>

            {/* Role & Persona Switcher */}
            <div className="relative">
              <button
                onClick={() => {
                  setShowUserMenu(!showUserMenu);
                  setShowCompanyMenu(false);
                }}
                className="flex items-center space-x-2 bg-slate-800/80 hover:bg-slate-750 px-2.5 py-1.5 rounded-lg border border-slate-700 transition"
                title="Switch User Role / Persona"
              >
                <div className="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold text-cyan-300">
                  {currentUser.avatar || currentUser.name.slice(0, 2)}
                </div>
                <div className="hidden lg:block text-left text-xs">
                  <div className="font-semibold text-slate-200 leading-tight">{currentUser.name.split(' ')[0]}</div>
                  <div className="text-[10px] text-cyan-400 leading-none">{currentUser.role}</div>
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-72 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl py-2 z-50">
                  <div className="px-3 py-2 border-b border-slate-800">
                    <p className="text-xs text-slate-400">Current Session</p>
                    <p className="text-sm font-bold text-white">{currentUser.name}</p>
                    <p className="text-xs text-slate-300">{currentUser.organization}</p>
                    <div className="mt-1">
                      <span className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded border ${getRoleBadgeColor(currentUser.role)}`}>
                        Role: {currentUser.role}
                      </span>
                    </div>
                  </div>

                  <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    Switch Test Persona
                  </div>

                  <div className="max-h-60 overflow-y-auto">
                    {availableUsers.map(user => (
                      <button
                        key={user.id}
                        onClick={() => {
                          onSwitchUser(user);
                          setShowUserMenu(false);
                        }}
                        className={`w-full text-left px-3 py-2 hover:bg-slate-800 transition flex items-center justify-between text-xs ${
                          user.id === currentUser.id ? 'bg-slate-800/90 text-cyan-300' : 'text-slate-300'
                        }`}
                      >
                        <div>
                          <div className="font-medium">{user.name}</div>
                          <div className="text-[11px] text-slate-400">{user.role} • {user.organization.split(' ')[0]}</div>
                        </div>
                        {user.id === currentUser.id && (
                          <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

          </div>

        </div>
      </div>
    </header>
  );
};
