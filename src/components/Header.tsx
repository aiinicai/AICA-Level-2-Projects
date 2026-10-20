import React from 'react';
import { User, Role } from '../types';
import { 
  Building2, 
  UserCheck, 
  Sparkles, 
  ShieldCheck, 
  Calculator, 
  FileText, 
  ChevronDown,
  PlusCircle,
  Briefcase,
  Target,
  Award,
  LogOut,
  Lock,
  RefreshCw,
  Download
} from 'lucide-react';

interface HeaderProps {
  currentUser: User;
  allUsers: User[];
  onSelectUser: (user: User) => void;
  activeTab: 'employee' | 'manager' | 'matrix' | 'certifications' | 'hr' | 'compliance' | 'reports' | 'audit' | 'simulator';
  onSelectTab: (tab: 'employee' | 'manager' | 'matrix' | 'certifications' | 'hr' | 'compliance' | 'reports' | 'audit' | 'simulator') => void;
  onOpenQuickEval: () => void;
  onOpenComplianceDoc: () => void;
  onLogout?: () => void;
  onResetSession?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentUser,
  allUsers,
  onSelectUser,
  activeTab,
  onSelectTab,
  onOpenQuickEval,
  onOpenComplianceDoc,
  onLogout,
  onResetSession,
}) => {
  const [showRoleMenu, setShowRoleMenu] = React.useState(false);

  const getRoleLabel = (role: Role) => {
    switch (role) {
      case 'super_admin': return 'Super Admin / Executive';
      case 'hr_manager': return 'HR Manager & Talent Lead';
      case 'department_manager': return 'Department Manager';
      case 'employee': return 'Employee Self-Service';
    }
  };

  const getRoleColor = (role: Role) => {
    switch (role) {
      case 'super_admin': return 'text-blue-900 bg-blue-100/80';
      case 'hr_manager': return 'text-teal-900 bg-teal-100/80';
      case 'department_manager': return 'text-indigo-900 bg-indigo-100/80';
      case 'employee': return 'text-slate-800 bg-slate-200/80';
    }
  };

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-xs">
      {/* Top Utility Bar for UAE Sovereign Organization Notice */}
      <div className="bg-slate-900 text-slate-300 text-xs py-1.5 px-6 flex items-center justify-between border-b border-slate-800">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-white tracking-wide flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5 text-teal-400" />
            Paras Accounting & Auditing Advisory
          </span>
          <span className="text-slate-500">|</span>
          <span className="text-slate-300">Abu Dhabi, UAE • Registered Audit Practice • Decree-Law No. 33/2021</span>
        </div>
        <div className="flex items-center gap-4 text-slate-300">
          <span className="tabular-nums">Cycle: Q3-2026 Evaluation</span>
          <span className="text-slate-500">•</span>
          <span className="text-teal-400 flex items-center gap-1">
            <Sparkles className="w-3 h-3" /> Growth-First Matrix Active
          </span>
          {onResetSession && (
            <button
              onClick={onResetSession}
              title="Reset session and restore initial enterprise state"
              className="text-[11px] text-slate-400 hover:text-white flex items-center gap-1 cursor-pointer transition-colors"
            >
              <RefreshCw className="w-3 h-3" /> Reset Session
            </button>
          )}
        </div>
      </div>

      {/* Main Top Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand Wordmark */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-900 via-blue-800 to-teal-700 flex items-center justify-center text-white font-black text-lg shadow-sm">
            P
          </div>
          <div>
            <a href="#" className="text-xl font-bold tracking-tight text-slate-950 whitespace-nowrap block leading-tight">
              PARAS <span className="text-teal-600 font-extrabold">ADVISORY</span>
            </a>
            <span className="text-[11px] font-medium text-slate-500 block leading-none">
              Performance & HR Intelligence Hub
            </span>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="hidden lg:flex items-center gap-1 text-sm font-medium text-slate-600">
          <button
            onClick={() => onSelectTab('employee')}
            className={`px-2.5 py-1.5 rounded-md transition-colors whitespace-nowrap shrink-0 flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'employee'
                ? 'bg-blue-50 text-blue-950 font-semibold border border-blue-200/60'
                : 'hover:text-slate-900 hover:bg-slate-100/70'
            }`}
          >
            <UserCheck className="w-4 h-4 text-blue-600" />
            Growth Hub
          </button>
          <button
            onClick={() => onSelectTab('manager')}
            className={`px-2.5 py-1.5 rounded-md transition-colors whitespace-nowrap shrink-0 flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'manager'
                ? 'bg-blue-50 text-blue-950 font-semibold border border-blue-200/60'
                : 'hover:text-slate-900 hover:bg-slate-100/70'
            }`}
          >
            <Briefcase className="w-4 h-4 text-teal-600" />
            Evaluations
          </button>
          <button
            onClick={() => onSelectTab('matrix')}
            className={`px-2.5 py-1.5 rounded-md transition-colors whitespace-nowrap shrink-0 flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'matrix'
                ? 'bg-blue-50 text-blue-950 font-semibold border border-blue-200/60'
                : 'hover:text-slate-900 hover:bg-slate-100/70'
            }`}
          >
            <Target className="w-4 h-4 text-teal-600" />
            Annual Matrix
          </button>
          <button
            onClick={() => onSelectTab('certifications')}
            className={`px-2.5 py-1.5 rounded-md transition-colors whitespace-nowrap shrink-0 flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'certifications'
                ? 'bg-amber-50 text-amber-950 font-semibold border border-amber-200/60'
                : 'hover:text-slate-900 hover:bg-slate-100/70'
            }`}
          >
            <Award className="w-4 h-4 text-amber-600" />
            AED 15k Bonus
          </button>
          <button
            onClick={() => onSelectTab('hr')}
            className={`px-2.5 py-1.5 rounded-md transition-colors whitespace-nowrap shrink-0 flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'hr'
                ? 'bg-blue-50 text-blue-950 font-semibold border border-blue-200/60'
                : 'hover:text-slate-900 hover:bg-slate-100/70'
            }`}
          >
            <Building2 className="w-4 h-4 text-blue-800" />
            HR Intelligence
          </button>
          <button
            onClick={() => onSelectTab('compliance')}
            className={`px-2.5 py-1.5 rounded-md transition-colors whitespace-nowrap shrink-0 flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'compliance'
                ? 'bg-rose-50 text-rose-950 font-semibold border border-rose-200/60'
                : 'hover:text-slate-900 hover:bg-slate-100/70'
            }`}
          >
            <ShieldCheck className="w-4 h-4 text-rose-600" />
            UAE Law
          </button>
          <button
            onClick={() => onSelectTab('reports')}
            className={`px-2.5 py-1.5 rounded-md transition-colors whitespace-nowrap shrink-0 flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'reports'
                ? 'bg-blue-900 text-white font-semibold shadow-xs'
                : 'text-blue-900 font-semibold hover:bg-blue-50/80'
            }`}
          >
            <FileText className="w-4 h-4 text-teal-400" />
            Reports
          </button>
          <button
            onClick={() => onSelectTab('audit')}
            className={`px-2.5 py-1.5 rounded-md transition-colors whitespace-nowrap shrink-0 flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'audit'
                ? 'bg-slate-900 text-teal-400 font-bold shadow-xs border border-slate-700'
                : 'text-slate-700 font-medium hover:text-slate-950 hover:bg-slate-100/70'
            }`}
          >
            <Lock className="w-4 h-4 text-teal-500" />
            Audit Trail
          </button>
          <button
            onClick={() => onSelectTab('simulator')}
            className={`px-2.5 py-1.5 rounded-md transition-colors whitespace-nowrap shrink-0 flex items-center gap-1.5 cursor-pointer ${
              activeTab === 'simulator'
                ? 'bg-teal-50 text-teal-950 font-semibold border border-teal-200/60'
                : 'hover:text-slate-900 hover:bg-slate-100/70'
            }`}
          >
            <Calculator className="w-4 h-4 text-teal-600" />
            Simulator
          </button>
        </nav>

        {/* Primary Action & Interactive Role Switcher */}
        <div className="flex items-center gap-2.5 shrink-0">
          <a
            href="/paras_advisory_capstone.zip"
            download="paras_advisory_capstone.zip"
            className="hidden sm:inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-lg shadow-xs transition-colors whitespace-nowrap cursor-pointer"
            title="Download clean capstone source package (.zip) for GitHub or Jury Review"
          >
            <Download className="w-4 h-4 text-teal-600" />
            Download Source .ZIP
          </a>

          <button
            onClick={onOpenQuickEval}
            className="hidden sm:inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-white bg-blue-700 hover:bg-blue-800 rounded-lg shadow-xs transition-colors whitespace-nowrap cursor-pointer"
          >
            <PlusCircle className="w-4 h-4 text-blue-200" />
            Log Points
          </button>

          {/* Role & Persona Switcher */}
          <div className="relative">
            <button
              onClick={() => setShowRoleMenu(!showRoleMenu)}
              className="flex items-center gap-2 p-1.5 pr-2.5 rounded-lg border border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50 transition-all text-left cursor-pointer"
              title="Click to switch persona (Mansoor, Tariq, Mariam, Zayed)"
            >
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-900 to-teal-700 text-white font-bold flex items-center justify-center text-xs shadow-2xs">
                {currentUser.fullName.split(' ').map((n) => n[0]).join('').slice(0, 2)}
              </div>
              <div className="hidden sm:block text-left">
                <div className="text-xs font-semibold text-slate-900 flex items-center gap-1.5">
                  <span className="truncate max-w-[120px]">{currentUser.fullName}</span>
                  <span className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${getRoleColor(currentUser.role)}`}>
                    {currentUser.role === 'super_admin' ? 'Executive' : currentUser.role === 'hr_manager' ? 'HR Head' : currentUser.role === 'department_manager' ? 'Partner' : 'Auditor'}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 truncate max-w-[150px]">
                  {currentUser.currentDesignation}
                </div>
              </div>
              <ChevronDown className="w-4 h-4 text-slate-400 ml-0.5" />
            </button>

            {/* Dropdown Menu */}
            {showRoleMenu && (
              <div 
                className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-xl border border-slate-200 py-2 z-50 animate-in fade-in slide-in-from-top-1"
                onClick={() => setShowRoleMenu(false)}
              >
                <div className="px-3.5 py-2 border-b border-slate-100">
                  <p className="text-xs font-bold text-slate-900">Switch Persona & Perspective</p>
                  <p className="text-[11px] text-slate-500">Persists session instantly without errors</p>
                </div>
                <div className="max-h-80 overflow-y-auto py-1 divide-y divide-slate-100">
                  {allUsers.map((user) => (
                    <button
                      key={user.id}
                      onClick={() => onSelectUser(user)}
                      className={`w-full px-3.5 py-2.5 flex items-center gap-3 text-left hover:bg-slate-50 transition-colors cursor-pointer ${
                        user.id === currentUser.id ? 'bg-blue-50/70' : ''
                      }`}
                    >
                      <div className="w-9 h-9 rounded-full bg-slate-100 text-slate-700 font-bold flex items-center justify-center text-xs shrink-0 border border-slate-200">
                        {user.fullName.split(' ').map((n) => n[0]).join('').slice(0, 2)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-bold text-slate-900 truncate">{user.fullName}</p>
                          <span className="text-[10px] text-slate-400 tabular-nums">{user.employeeIdCode}</span>
                        </div>
                        <p className="text-[11px] text-slate-500 truncate">{user.currentDesignation}</p>
                        <div className="flex items-center gap-2 mt-0.5 text-[10px]">
                          <span className="font-semibold text-teal-700">
                            {getRoleLabel(user.role)}
                          </span>
                          <span className="text-slate-300">•</span>
                          <span className="text-slate-500 tabular-nums">{user.tenureYears} yrs tenure</span>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
                <div className="p-2 border-t border-slate-100 bg-slate-50/50 flex justify-between items-center text-[11px] text-slate-500 px-3">
                  <span>Current: {getRoleLabel(currentUser.role)}</span>
                  {onLogout && (
                    <button
                      onClick={onLogout}
                      className="text-slate-600 hover:text-rose-700 font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                    >
                      <LogOut className="w-3.5 h-3.5" /> Log Out
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>

          {onLogout && (
            <button
              onClick={onLogout}
              className="p-2 text-slate-400 hover:text-rose-700 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
              title="Log out to Portal Landing Screen"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
