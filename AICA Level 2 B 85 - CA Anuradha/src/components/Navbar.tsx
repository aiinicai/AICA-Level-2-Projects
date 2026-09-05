import React from 'react';
import { useApp } from '../context/AppContext';
import {
  Calendar,
  IndianRupee,
  DollarSign,
  TrendingUp,
  FileText,
  History,
  Download,
  RotateCcw,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Lock,
  Sparkles,
} from 'lucide-react';
import { formatAUD, formatINR } from '../utils/formatters';
import { exportConsolidatedToCSV, exportDepartmentSummaryToCSV } from '../utils/exportCsv';

interface NavbarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  onOpenAuditTrail: () => void;
  onOpenApprovalSummary: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  setCurrentTab,
  onOpenAuditTrail,
  onOpenApprovalSummary,
}) => {
  const {
    currentUser,
    months,
    activeMonthId,
    setActiveMonthId,
    activeMonth,
    currencyMode,
    setCurrencyMode,
    currentSubmissions,
    resetToInitialData,
  } = useApp();

  const getMonthStatusBadge = () => {
    switch (activeMonth.status) {
      case 'Open':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
            Open for Input
          </span>
        );
      case 'Ready for Approval':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
            <Lock className="w-3 h-3 text-blue-600" />
            Pack Locked / In Review
          </span>
        );
      case 'Approved':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            Approved by Management
          </span>
        );
      case 'Closed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
            <Lock className="w-3 h-3 text-slate-500" />
            Closed
          </span>
        );
    }
  };

  const handleExportCSV = () => {
    exportConsolidatedToCSV(activeMonth, currentSubmissions);
  };

  // Determine available tabs based on role
  const getTabsForRole = () => {
    const tabs: { id: string; label: string; icon: React.ReactNode }[] = [];

    if (currentUser.role === 'department_submitter') {
      tabs.push({
        id: 'dept_form',
        label: `${currentUser.department || ''} Cash Input`,
        icon: <FileText className="w-4 h-4" />,
      });
      tabs.push({
        id: 'dashboard',
        label: 'Consolidated View',
        icon: <TrendingUp className="w-4 h-4" />,
      });
    } else if (currentUser.role === 'finance_controller') {
      tabs.push({
        id: 'controller_view',
        label: 'Controller Review & FX',
        icon: <Sliders className="w-4 h-4" />,
      });
      tabs.push({
        id: 'dashboard',
        label: 'Consolidated Dashboard',
        icon: <TrendingUp className="w-4 h-4" />,
      });
    } else if (currentUser.role === 'management') {
      tabs.push({
        id: 'dashboard',
        label: 'Management Dashboard',
        icon: <TrendingUp className="w-4 h-4" />,
      });
      tabs.push({
        id: 'controller_view',
        label: 'Review Pack Details',
        icon: <Sliders className="w-4 h-4" />,
      });
    } else if (currentUser.role === 'admin') {
      tabs.push({
        id: 'dashboard',
        label: 'Executive Overview',
        icon: <TrendingUp className="w-4 h-4" />,
      });
      tabs.push({
        id: 'admin_settings',
        label: 'Admin Settings & Categories',
        icon: <Sliders className="w-4 h-4" />,
      });
    }

    return tabs;
  };

  return (
    <header className="bg-white border-b border-slate-200 shadow-sm sticky top-[41px] z-40">
      {/* Top Main Navigation Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          
          {/* Logo and Brand */}
          <div className="flex items-center gap-3.5">
            <div className="w-9 h-9 rounded-lg bg-[#0F172A] flex items-center justify-center text-white font-black shadow-sm">
              <span className="text-lg tracking-tight">M</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold tracking-tight text-slate-900">
                  MAROPOST <span className="text-blue-600">INDIA</span>
                </h1>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 bg-slate-100 text-slate-700 rounded border border-slate-200">
                  Treasury & FP&A
                </span>
              </div>
              <p className="text-[10px] text-slate-400 uppercase tracking-widest mt-0.5 font-semibold">
                Cash Management & Currency Authorization
              </p>
            </div>
          </div>

          {/* Controls: Month Selector + Currency Display + Rate Pill + Quick Actions */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            
            {/* Month Cycle Selector */}
            <div className="flex items-center gap-1.5 bg-[#F1F5F9] p-1 rounded-lg border border-slate-200">
              <Calendar className="w-3.5 h-3.5 text-slate-500 ml-1.5" />
              <select
                id="active-month-select"
                value={activeMonthId}
                onChange={(e) => setActiveMonthId(e.target.value)}
                className="bg-transparent text-xs font-bold text-slate-800 pr-2 py-0.5 focus:outline-none cursor-pointer"
              >
                {months.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label} ({m.status})
                  </option>
                ))}
              </select>
              {getMonthStatusBadge()}
            </div>

            {/* Live Exchange Rate Pill */}
            <div
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold"
              title={`Source: ${activeMonth.rateSource || 'RBI Reference Rate'}`}
            >
              <span className="text-emerald-700 font-bold uppercase text-[10px] tracking-wider">Exchange Rate</span>
              <span className="font-mono font-bold">1 AUD = {(1 / activeMonth.exchangeRate).toFixed(2)} INR</span>
              <span className="text-emerald-600 text-[10px] font-normal">
                (1 INR = A${activeMonth.exchangeRate})
              </span>
            </div>

            {/* Currency Mode Switcher */}
            <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs">
              <button
                id="currency-mode-both"
                onClick={() => setCurrencyMode('both')}
                className={`px-2 py-1 rounded-md font-bold text-xs transition-all ${
                  currencyMode === 'both'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
                title="Display both INR and AUD"
              >
                Dual (₹+A$)
              </button>
              <button
                id="currency-mode-inr"
                onClick={() => setCurrencyMode('inr')}
                className={`px-2 py-1 rounded-md font-bold text-xs transition-all ${
                  currencyMode === 'inr'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
                title="Focus INR (₹)"
              >
                ₹ INR
              </button>
              <button
                id="currency-mode-aud"
                onClick={() => setCurrencyMode('aud')}
                className={`px-2 py-1 rounded-md font-bold text-xs transition-all ${
                  currencyMode === 'aud'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
                title="Focus AUD (A$)"
              >
                A$ AUD
              </button>
            </div>

            {/* Export & Actions Dropdown / Buttons */}
            <div className="flex items-center gap-1.5">
              <button
                id="btn-signoff-summary"
                onClick={onOpenApprovalSummary}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-bold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg shadow-xs transition-colors"
                title="View printable Sign-off Summary"
              >
                <FileText className="w-3.5 h-3.5 text-blue-600" />
                <span className="hidden sm:inline">Sign-off Sheet</span>
              </button>

              <button
                id="btn-export-csv"
                onClick={handleExportCSV}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-bold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg shadow-xs transition-colors"
                title="Download CSV report"
              >
                <Download className="w-3.5 h-3.5 text-slate-600" />
                <span className="hidden sm:inline">Export CSV</span>
              </button>

              <button
                id="btn-audit-trail"
                onClick={onOpenAuditTrail}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-bold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg shadow-xs transition-colors"
                title="View full audit trail & history"
              >
                <History className="w-3.5 h-3.5 text-amber-600" />
                <span className="hidden md:inline">Audit Trail</span>
              </button>

              <button
                id="btn-reset-demo"
                onClick={() => {
                  if (confirm('Reset all demo state to fresh initial seed data?')) {
                    resetToInitialData();
                  }
                }}
                className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
                title="Reset application data to initial demo state"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>

          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-2 mt-3 pt-2.5 border-t border-slate-100 overflow-x-auto">
          {getTabsForRole().map((tab) => {
            const isActive = currentTab === tab.id;
            return (
              <button
                key={tab.id}
                id={`nav-tab-${tab.id}`}
                onClick={() => setCurrentTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition-all ${
                  isActive
                    ? 'bg-[#0F172A] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
