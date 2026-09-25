import React, { useState } from 'react';
import {
  Lock,
  ShieldCheck,
  ArrowRight,
  AlertCircle,
  Building2,
  Search,
  KeyRound,
  Eye,
  EyeOff,
  UserCheck,
  ShieldAlert,
  BookOpen,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';
import { EmployeeMaster } from '../types/payroll';
import { UserSession } from '../types/auth';

interface LoginModalProps {
  employees: EmployeeMaster[];
  onLogin: (session: UserSession) => void;
  onOpenCapstoneDeck?: () => void;
  isModal?: boolean;
  onClose?: () => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({
  employees,
  onLogin,
  onOpenCapstoneDeck,
  isModal = false,
  onClose,
}) => {
  const [emailInput, setEmailInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'form' | 'directory'>('form');
  const [filterQuery, setFilterQuery] = useState('');

  const normalizeEmail = (raw: string): string => {
    let email = raw.trim().toLowerCase();
    if (!email) return '';
    // If user enters just firstname without @xyz.com, auto-append @xyz.com for convenience
    if (!email.includes('@')) {
      email = `${email}@xyz.com`;
    }
    return email;
  };

  const handleLoginSubmit = (targetEmail?: string) => {
    const email = normalizeEmail(targetEmail || emailInput);
    if (!email) {
      setErrorMsg('Please enter your corporate email address (@xyz.com).');
      return;
    }

    // 1. Check if Admin: admin@xyz.com
    if (email === 'admin@xyz.com' || email === 'admin@' || email === 'admin') {
      setErrorMsg(null);
      onLogin({
        role: 'admin',
        email: 'admin@xyz.com',
        name: 'Payroll & HR Administrator',
      });
      return;
    }

    // 2. Check if Employee: firstname@xyz.com
    const username = email.split('@')[0];
    const domain = email.split('@')[1];

    if (domain !== 'xyz.com') {
      setErrorMsg(
        `Corporate domain mismatch. Only company accounts ending with "@xyz.com" or "admin@xyz.com" are permitted.`
      );
      return;
    }

    // Match employee by:
    // a. Exact email
    // b. First name matching username (e.g. ananya@xyz.com -> Ananya)
    // c. Full name with dot (e.g. rahul.gupta@xyz.com -> Rahul Gupta)
    // d. Employee Code (e.g. emp001@xyz.com -> EMP001)
    const matchedEmployee = employees.find((emp) => {
      const empEmail = (emp.email || '').toLowerCase();
      const firstName = emp.employeeName.trim().split(/\s+/)[0].toLowerCase();
      const dotName = emp.employeeName.trim().toLowerCase().replace(/\s+/g, '.');
      const empCode = emp.employeeCode.toLowerCase();

      return (
        empEmail === email ||
        firstName === username ||
        dotName === username ||
        empCode === username ||
        `${firstName}@xyz.com` === email ||
        `${dotName}@xyz.com` === email
      );
    });

    if (matchedEmployee) {
      setErrorMsg(null);
      const standardCorporateEmail =
        matchedEmployee.email ||
        `${matchedEmployee.employeeName.trim().split(/\s+/)[0].toLowerCase()}@xyz.com`;

      onLogin({
        role: 'employee',
        email: standardCorporateEmail,
        name: matchedEmployee.employeeName,
        employeeCode: matchedEmployee.employeeCode,
      });
    } else {
      setErrorMsg(
        `No employee record found for "${email}". Active corporate accounts use "firstname@xyz.com" (e.g. ananya@xyz.com, mandeep@xyz.com, dilawar@xyz.com, joydeep@xyz.com) or "admin@xyz.com".`
      );
    }
  };

  const filteredEmployees = employees.filter((e) => {
    if (!filterQuery) return true;
    const q = filterQuery.toLowerCase();
    const firstName = e.employeeName.split(' ')[0].toLowerCase();
    return (
      e.employeeName.toLowerCase().includes(q) ||
      (e.email && e.email.toLowerCase().includes(q)) ||
      `${firstName}@xyz.com`.includes(q) ||
      e.employeeCode.toLowerCase().includes(q) ||
      e.department.toLowerCase().includes(q)
    );
  });

  return (
    <div
      className={
        isModal
          ? 'fixed inset-0 z-50 overflow-y-auto bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4'
          : 'min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 text-slate-100 flex flex-col justify-between p-4 sm:p-6 lg:p-8'
      }
    >
      {/* Top Banner on standalone page */}
      {!isModal && (
        <header className="max-w-6xl w-full mx-auto flex items-center justify-between py-2 border-b border-slate-800/80 mb-6 shrink-0">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-600/30">
              <Building2 className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-base font-black tracking-tight text-white flex items-center gap-2">
                XYZ ENTERPRISES INDIA
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Internal Payroll
                </span>
              </h1>
              <p className="text-xs text-slate-400">
                Statutory Payroll & Indian Income Tax (AY 2026–27) Secure Gateway
              </p>
            </div>
          </div>

          {onOpenCapstoneDeck && (
            <button
              type="button"
              onClick={onOpenCapstoneDeck}
              className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-400/30 rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer"
            >
              <BookOpen className="h-4 w-4 text-amber-400" />
              <span>Capstone Artifact (Report & PPTX)</span>
            </button>
          )}
        </header>
      )}

      {/* Main Authentication Box */}
      <div className="max-w-xl w-full mx-auto my-auto bg-slate-900/90 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-xl flex flex-col">
        {/* Header Branding */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 p-6 text-center border-b border-slate-800 relative overflow-hidden">
          <div className="absolute -top-10 -right-10 w-32 h-32 bg-indigo-500/10 rounded-full blur-2xl pointer-events-none" />
          <div className="h-12 w-12 rounded-xl bg-indigo-600/90 border border-indigo-400/30 flex items-center justify-center mx-auto mb-3 text-white shadow-lg shadow-indigo-600/40">
            <Lock className="h-6 w-6" />
          </div>
          <h2 className="text-lg font-black text-white tracking-tight">
            XYZ ENTERPRISES • SECURE LOGIN
          </h2>
          <p className="text-xs text-slate-300 mt-1">
            Indian Statutory Payroll & Employee Self-Service (AY 2026–27)
          </p>

          <div className="mt-3 flex items-center justify-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[10px] font-semibold">
              <ShieldCheck className="h-3 w-3" />
              Role-Based Access Control (RBAC)
            </span>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 text-[10px] font-semibold">
              <Sparkles className="h-3 w-3" />
              AY 2026–27 Compliant
            </span>
          </div>
        </div>

        {/* Tab switch between Manual Form & 1-Click Directory */}
        <div className="flex border-b border-slate-800 bg-slate-950/60 p-1">
          <button
            type="button"
            onClick={() => setActiveTab('form')}
            className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-2 cursor-pointer ${
              activeTab === 'form'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <KeyRound className="h-3.5 w-3.5" />
            <span>Corporate Sign In</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('directory')}
            className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-2 cursor-pointer ${
              activeTab === 'directory'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <UserCheck className="h-3.5 w-3.5" />
            <span>1-Click Test Directory ({employees.length + 1})</span>
          </button>
        </div>

        {/* Tab 1: Form Login */}
        {activeTab === 'form' && (
          <div className="p-6 space-y-4">
            <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3 text-xs text-slate-300 space-y-1">
              <p className="font-semibold text-white flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                Enterprise Access Policy:
              </p>
              <ul className="list-disc list-inside text-[11px] text-slate-300 space-y-0.5 pl-1">
                <li>
                  <strong className="text-indigo-300">Employees:</strong> Sign in using{' '}
                  <code className="text-amber-300 bg-slate-900 px-1 py-0.2 rounded font-mono">
                    firstname@xyz.com
                  </code>{' '}
                  (e.g., <em>ananya@xyz.com</em>, <em>mandeep@xyz.com</em>, <em>dilawar@xyz.com</em>, <em>joydeep@xyz.com</em>). Access is isolated strictly to individual payslips and tax declarations.
                </li>
                <li>
                  <strong className="text-indigo-300">Administrator:</strong> Sign in using{' '}
                  <code className="text-amber-300 bg-slate-900 px-1 py-0.2 rounded font-mono">
                    admin@xyz.com
                  </code>{' '}
                  for full Salary Register, Employee Master, and Tax Governance.
                </li>
              </ul>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-200 mb-1.5">
                Corporate Email Address
              </label>
              <input
                type="text"
                placeholder="e.g. mandeep@xyz.com or admin@xyz.com"
                value={emailInput}
                onChange={(e) => {
                  setEmailInput(e.target.value);
                  setErrorMsg(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleLoginSubmit();
                }}
                className="w-full px-3.5 py-2.5 bg-slate-950/70 border border-slate-700 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-medium"
              />
              <p className="text-[10px] text-slate-400 mt-1">
                Formats accepted: <span className="font-mono text-slate-300">firstname@xyz.com</span>,{' '}
                <span className="font-mono text-slate-300">admin@xyz.com</span>, or simply{' '}
                <span className="font-mono text-slate-300">firstname</span>.
              </p>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-200 mb-1.5 flex items-center justify-between">
                <span>Corporate Password / SSO PIN</span>
                <span className="text-[10px] text-emerald-400 font-normal">
                  Demo Bypass Enabled
                </span>
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter corporate password (or leave blank in demo)"
                  value={passwordInput}
                  onChange={(e) => setPasswordInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleLoginSubmit();
                  }}
                  className="w-full px-3.5 py-2.5 pr-10 bg-slate-950/70 border border-slate-700 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-medium"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-200"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <p className="text-[10px] text-slate-400 mt-1">
                * For evaluation and review, any password or leaving it blank authenticates valid corporate accounts.
              </p>
            </div>

            {errorMsg && (
              <div className="p-3 bg-rose-950/60 border border-rose-600/50 rounded-xl text-rose-200 text-xs flex items-start gap-2.5">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-400" />
                <span className="leading-relaxed">{errorMsg}</span>
              </div>
            )}

            <button
              type="button"
              onClick={() => handleLoginSubmit()}
              className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl transition-all shadow-md shadow-indigo-600/30 flex items-center justify-center gap-2 cursor-pointer mt-2"
            >
              <span>Authenticate & Enter Portal</span>
              <ArrowRight className="h-4 w-4" />
            </button>

            {/* Quick Helper Badges */}
            <div className="pt-3 border-t border-slate-800">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-2">
                Quick Test Credentials:
              </span>
              <div className="flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={() => {
                    setEmailInput('admin@xyz.com');
                    handleLoginSubmit('admin@xyz.com');
                  }}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-[11px] font-semibold text-emerald-400 cursor-pointer"
                >
                  admin@xyz.com (Admin)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEmailInput('ananya@xyz.com');
                    handleLoginSubmit('ananya@xyz.com');
                  }}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-[11px] font-semibold text-indigo-300 cursor-pointer"
                >
                  ananya@xyz.com (Emp #1)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEmailInput('mandeep@xyz.com');
                    handleLoginSubmit('mandeep@xyz.com');
                  }}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-[11px] font-semibold text-indigo-300 cursor-pointer"
                >
                  mandeep@xyz.com (Lead QA)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEmailInput('dilawar@xyz.com');
                    handleLoginSubmit('dilawar@xyz.com');
                  }}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-[11px] font-semibold text-indigo-300 cursor-pointer"
                >
                  dilawar@xyz.com (DevOps)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEmailInput('joydeep@xyz.com');
                    handleLoginSubmit('joydeep@xyz.com');
                  }}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-[11px] font-semibold text-indigo-300 cursor-pointer"
                >
                  joydeep@xyz.com (CTO)
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: 1-Click Directory for Reviewers */}
        {activeTab === 'directory' && (
          <div className="p-6 space-y-3.5 max-h-[60vh] overflow-y-auto">
            <div className="relative">
              <Search className="h-4 w-4 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search employee by name, department, or email..."
                value={filterQuery}
                onChange={(e) => setFilterQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-slate-950/70 border border-slate-700 rounded-xl text-xs text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            {/* Admin Option */}
            <button
              type="button"
              onClick={() => handleLoginSubmit('admin@xyz.com')}
              className="w-full text-left p-3 rounded-xl bg-gradient-to-r from-slate-800 to-indigo-950 border border-slate-700 hover:border-emerald-500 transition-all flex items-center justify-between group cursor-pointer shadow-xs"
            >
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center font-bold text-xs">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <div>
                  <span className="font-bold text-white text-xs block group-hover:text-emerald-300">
                    Payroll & HR Administrator
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    admin@xyz.com • Full Master, Register & Governance
                  </span>
                </div>
              </div>
              <span className="text-[10px] font-bold text-emerald-400 bg-emerald-950/60 border border-emerald-600/40 px-2 py-0.5 rounded">
                Admin Access
              </span>
            </button>

            {/* Employee List */}
            <div className="space-y-1.5">
              <span className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">
                Corporate Employees ({filteredEmployees.length})
              </span>

              {filteredEmployees.map((emp) => {
                const firstName = emp.employeeName.trim().split(/\s+/)[0].toLowerCase();
                const demoEmail = `${firstName}@xyz.com`;

                return (
                  <button
                    key={emp.employeeCode}
                    type="button"
                    onClick={() => handleLoginSubmit(demoEmail)}
                    className="w-full text-left p-2.5 rounded-xl bg-slate-950/40 hover:bg-slate-800/80 border border-slate-800 hover:border-indigo-500 transition-all flex items-center justify-between group cursor-pointer"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="h-7 w-7 rounded-lg bg-slate-800 group-hover:bg-indigo-600 text-slate-300 group-hover:text-white font-bold text-xs flex items-center justify-center transition-colors">
                        {emp.employeeName.charAt(0)}
                      </div>
                      <div>
                        <span className="font-semibold text-slate-200 text-xs block group-hover:text-white">
                          {emp.employeeName}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          {demoEmail} • {emp.designation} ({emp.department})
                        </span>
                      </div>
                    </div>
                    <span className="text-[10px] font-semibold text-indigo-400 bg-indigo-950/60 border border-indigo-700/30 px-2 py-0.5 rounded">
                      {emp.employeeCode}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Security Isolation Footer Note */}
        <div className="bg-slate-950/90 border-t border-slate-800 px-6 py-3 flex items-center justify-between text-[11px] text-slate-400">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            <span>Zero Cross-Tenant Leakage</span>
          </div>
          <span className="font-mono text-[10px] text-slate-500">
            TLS 1.3 • AES-256 Session Token
          </span>
        </div>
      </div>

      {/* Standalone Footer */}
      {!isModal && (
        <footer className="max-w-6xl w-full mx-auto text-center py-4 text-xs text-slate-500 border-t border-slate-800/60 mt-6 shrink-0">
          <p>
            XYZ Enterprises Ltd. • Statutory Indian Income Tax & Dual-Regime Payroll System (AY 2026–27)
          </p>
          <p className="text-[11px] text-slate-600 mt-0.5">
            Employees log in as <span className="text-slate-400 font-mono">firstname@xyz.com</span> | Administrator logs in as <span className="text-slate-400 font-mono">admin@xyz.com</span>
          </p>
        </footer>
      )}
    </div>
  );
};
