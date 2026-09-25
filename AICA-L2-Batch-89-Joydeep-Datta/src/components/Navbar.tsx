import React from 'react';
import {
  Calculator,
  Users,
  FileSpreadsheet,
  Scale,
  ShieldCheck,
  Calendar,
  Layers,
  User,
  LogOut,
  Lock,
  Presentation,
  BookOpen,
} from 'lucide-react';
import { FY_MONTHS } from '../utils/payrollEngine';
import { TaxConfig } from '../types/payroll';
import { UserSession } from '../types/auth';

export type NavigationTab = 'payroll' | 'employees' | 'declarations' | 'simulator' | 'governance' | 'my-portal';

export interface NavbarProps {
  activeTab: NavigationTab;
  onTabChange?: (tab: NavigationTab) => void;
  setActiveTab?: (tab: NavigationTab) => void;
  selectedMonth: number;
  onMonthChange?: (month: number) => void;
  setSelectedMonth?: (month: number) => void;
  selectedFy: string;
  onFyChange?: (fy: string) => void;
  setSelectedFy?: (fy: string) => void;
  taxConfig?: TaxConfig;
  employeeCount?: number;
  userSession?: UserSession | null;
  onLogout?: () => void;
  onOpenLogin?: () => void;
  onOpenCapstoneDeck?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onTabChange,
  setActiveTab,
  selectedMonth,
  onMonthChange,
  setSelectedMonth,
  selectedFy,
  onFyChange,
  setSelectedFy,
  taxConfig,
  employeeCount = 5,
  userSession,
  onLogout,
  onOpenLogin,
  onOpenCapstoneDeck,
}) => {
  const handleTabSelect = (tab: NavigationTab) => {
    if (onTabChange) onTabChange(tab);
    if (setActiveTab) setActiveTab(tab);
  };

  const handleMonthSelect = (m: number) => {
    if (onMonthChange) onMonthChange(m);
    if (setSelectedMonth) setSelectedMonth(m);
  };

  const handleFySelect = (fy: string) => {
    if (onFyChange) onFyChange(fy);
    if (setSelectedFy) setSelectedFy(fy);
  };

  const isEmployee = userSession?.role === 'employee';

  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-30 shadow-xs">
      {/* Top bar: Branding, FY switcher, Month switcher, Audit badge & Session */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between py-3 gap-3">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-xs shrink-0">
              <Calculator className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-black text-slate-900 tracking-tight">
                  {isEmployee ? 'EMPLOYEE SELF-SERVICE' : 'ACME PAYROLL & TDS'}
                </h1>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200">
                  AY 2026–27
                </span>
              </div>
              <p className="text-xs text-slate-500">
                {isEmployee
                  ? 'Your personal salary slips, dual-regime tax simulator & declarations'
                  : 'Statutory dual-regime income tax, calendar proration & salary processing'}
              </p>
            </div>
          </div>

          {/* Controls: Financial Year, Month & Session Profile */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            {/* Financial Year Selector */}
            <div className="flex items-center bg-slate-50 border border-slate-200 rounded-lg p-1">
              <span className="text-xs font-medium text-slate-500 px-2 flex items-center gap-1">
                <Layers className="h-3.5 w-3.5 text-slate-400" /> FY:
              </span>
              <select
                value={selectedFy}
                onChange={(e) => handleFySelect(e.target.value)}
                className="bg-white text-xs font-semibold text-slate-800 border border-slate-200 rounded px-2.5 py-1 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="2026-27">2026–27</option>
                <option value="2025-26">2025–26</option>
              </select>
            </div>

            {/* Payroll Month Selector */}
            <div className="flex items-center bg-slate-50 border border-slate-200 rounded-lg p-1">
              <span className="text-xs font-medium text-slate-500 px-2 flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5 text-slate-400" /> Month:
              </span>
              <select
                value={selectedMonth}
                onChange={(e) => handleMonthSelect(Number(e.target.value))}
                className="bg-white text-xs font-semibold text-slate-800 border border-slate-200 rounded px-2.5 py-1 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                {FY_MONTHS.map((m) => (
                  <option key={m.index} value={m.index}>
                    M{m.index}: {m.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Statutory Hash Audit Badge (visible in Admin view) */}
            {!isEmployee && (
              <div
                onClick={() => handleTabSelect('governance')}
                className="cursor-pointer group flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-lg text-xs hover:bg-emerald-100 transition-colors hidden lg:flex"
                title="Click to view tax rates governance & cryptographic stamp"
              >
                <ShieldCheck className="h-4 w-4 text-emerald-600 shrink-0" />
                <div className="flex flex-col">
                  <span className="font-semibold text-emerald-800 text-[11px] leading-tight">
                    TaxConfig {taxConfig?.financialYear || selectedFy}
                  </span>
                  <span className="text-[10px] text-emerald-600 font-mono leading-tight">
                    sha256:{taxConfig ? taxConfig.approval.contentSha256.substring(0, 8) : 'e3b0c442'}...
                  </span>
                </div>
              </div>
            )}

            {/* Capstone Report Artifact & Deck Presentation Button */}
            {onOpenCapstoneDeck && (
              <button
                type="button"
                onClick={onOpenCapstoneDeck}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-indigo-600 via-indigo-700 to-purple-700 hover:from-indigo-500 hover:to-purple-600 text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer border border-indigo-400/30 shrink-0"
                title="View Full Capstone Report Artifact & Presentation Deck (.pptx)"
              >
                <BookOpen className="h-4 w-4 text-amber-300" />
                <span className="hidden sm:inline">Capstone Artifact</span>
                <span className="text-[10px] bg-amber-400 text-slate-900 px-1 py-0.2 rounded font-extrabold">
                  Report & PPTX
                </span>
              </button>
            )}

            {/* Session Pill */}
            {userSession ? (
              <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
                <div className="flex items-center gap-2 px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs">
                  <div
                    className={`h-6 w-6 rounded-full flex items-center justify-center font-bold text-[10px] ${
                      isEmployee ? 'bg-indigo-600 text-white' : 'bg-slate-900 text-white'
                    }`}
                  >
                    {userSession.name.charAt(0)}
                  </div>
                  <div className="flex flex-col text-left">
                    <span className="font-bold text-slate-800 text-[11px] leading-tight flex items-center gap-1">
                      {userSession.name}
                      <span
                        className={`text-[9px] px-1 py-0.2 rounded font-semibold ${
                          isEmployee ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-200 text-slate-800'
                        }`}
                      >
                        {isEmployee ? 'Employee' : 'HR Admin'}
                      </span>
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono leading-tight">
                      {userSession.email}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={onLogout}
                  className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
                  title="Switch user or logout"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={onOpenLogin}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-colors shadow-xs cursor-pointer"
              >
                <Lock className="h-3.5 w-3.5" />
                <span>Sign In</span>
              </button>
            )}
          </div>
        </div>

        {/* Tab Navigation */}
        <nav className="flex space-x-1 border-t border-slate-100 pt-1 overflow-x-auto" aria-label="Tabs">
          {isEmployee ? (
            /* Employee Self-Service Navigation */
            <button
              onClick={() => handleTabSelect('my-portal')}
              className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors cursor-pointer ${
                activeTab === 'my-portal'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
              }`}
            >
              <User className="h-4 w-4" />
              My Employee Self-Service Portal
            </button>
          ) : (
            /* Admin Full Navigation */
            <>
              <button
                onClick={() => handleTabSelect('payroll')}
                className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors cursor-pointer ${
                  activeTab === 'payroll'
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
                }`}
              >
                <Calculator className="h-4 w-4" />
                Company Salary Register
              </button>

              <button
                onClick={() => handleTabSelect('employees')}
                className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors cursor-pointer ${
                  activeTab === 'employees'
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
                }`}
              >
                <Users className="h-4 w-4" />
                Employee Master
                <span className="ml-1 px-1.5 py-0.5 rounded-full text-[10px] bg-slate-100 text-slate-700">
                  {employeeCount}
                </span>
              </button>

              <button
                onClick={() => handleTabSelect('declarations')}
                className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors cursor-pointer ${
                  activeTab === 'declarations'
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
                }`}
              >
                <FileSpreadsheet className="h-4 w-4" />
                All Tax Declarations (TDS)
              </button>

              <button
                onClick={() => handleTabSelect('simulator')}
                className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors cursor-pointer ${
                  activeTab === 'simulator'
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
                }`}
              >
                <Scale className="h-4 w-4" />
                Dual-Regime Simulator
              </button>

              <button
                onClick={() => handleTabSelect('governance')}
                className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors cursor-pointer ${
                  activeTab === 'governance'
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
                }`}
              >
                <ShieldCheck className="h-4 w-4" />
                Tax Slabs & Governance (AY 2026–27)
              </button>

              <button
                onClick={() => handleTabSelect('my-portal')}
                className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors ml-auto cursor-pointer ${
                  activeTab === 'my-portal'
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-indigo-700 bg-indigo-50/70 hover:bg-indigo-100/70 rounded-t-lg'
                }`}
              >
                <User className="h-4 w-4" />
                View as Employee
              </button>
            </>
          )}
        </nav>
      </div>
    </header>
  );
};
