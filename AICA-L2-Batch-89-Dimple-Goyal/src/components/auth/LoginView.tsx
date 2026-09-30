import React, { useState } from 'react';
import {
  ShieldCheck,
  Lock,
  User as UserIcon,
  Eye,
  EyeOff,
  ArrowRight,
  Building2,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
  KeyRound,
  Check
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { DEMO_USERS } from '../../data/demoData';

export const LoginView: React.FC = () => {
  const { login, resetToDemoData } = useApp();
  const [userIdInput, setUserIdInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessNotice(null);

    if (!userIdInput.trim()) {
      setErrorMessage('Please enter your User ID or Registered Email.');
      return;
    }
    if (!passwordInput) {
      setErrorMessage('Please enter your Password.');
      return;
    }

    setIsLoading(true);
    try {
      const result = login(userIdInput.trim(), passwordInput);
      if (!result.success) {
        setIsLoading(false);
        setErrorMessage(result.message || 'Invalid User ID or Password. Please try again.');
      }
    } catch (err: any) {
      setIsLoading(false);
      setErrorMessage(err?.message || 'Login error occurred.');
    }
  };

  const handleQuickLogin = (demoUserId: string, demoPass: string) => {
    setUserIdInput(demoUserId);
    setPasswordInput(demoPass);
    setErrorMessage(null);
    setSuccessNotice(null);
    setIsLoading(true);
    try {
      const result = login(demoUserId, demoPass);
      if (!result.success) {
        setIsLoading(false);
        setErrorMessage(result.message || 'Login failed. Please check credentials.');
      }
    } catch (err: any) {
      setIsLoading(false);
      setErrorMessage(err?.message || 'Login error occurred.');
    }
  };

  const handleFillOnly = (demoUserId: string, demoPass: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setUserIdInput(demoUserId);
    setPasswordInput(demoPass);
    setErrorMessage(null);
    setSuccessNotice(`Pre-filled credentials for ${demoUserId}. Click "Verify & Sign In".`);
  };

  const handleResetAccounts = () => {
    if (window.confirm('Restore all default test user IDs and passwords?')) {
      resetToDemoData();
      setUserIdInput('dimple.admin');
      setPasswordInput('Admin@2026');
      setSuccessNotice('Default test accounts restored successfully. Dimple Agrawal (Business Owner) credentials loaded.');
      setErrorMessage(null);
    }
  };

  return (
    <div className="min-h-screen w-screen bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-950 flex flex-col justify-between p-4 sm:p-6 lg:p-8 text-slate-100 font-sans">
      {/* Top Header */}
      <div className="max-w-6xl w-full mx-auto flex items-center justify-between py-2">
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center font-black text-xl text-white shadow-lg shadow-emerald-900/50">
            ₹
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold tracking-tight text-lg text-white">FinRecon India</span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                FY 2026-27
              </span>
            </div>
            <p className="text-xs text-slate-400">Multi-Entity Receivables, Bank Reconciliation & Statutory Tax Audit</p>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-2 text-xs text-emerald-400 bg-emerald-950/60 px-3 py-1.5 rounded-full border border-emerald-800/60">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Role-Based Access Control (RBAC) Active</span>
        </div>
      </div>

      {/* Main Grid: Login Box + Credentials Info */}
      <div className="max-w-6xl w-full mx-auto my-6 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
        {/* Left Column: Platform Highlights */}
        <div className="lg:col-span-5 space-y-6">
          <div className="space-y-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
              <ShieldCheck className="w-3.5 h-3.5" />
              Secure Enterprise Gateway
            </span>
            <h1 className="text-3xl sm:text-4xl font-black text-white tracking-tight leading-tight">
              Unified Financial Books & Reconciliations
            </h1>
            <p className="text-sm text-slate-300 leading-relaxed">
              Login with your verified User ID and Password to manage company ledgers, auto-reconcile bank receipts, verify 26AS/AIS TDS credits, and audit GSTR-1 filings.
            </p>
          </div>

          <div className="space-y-3 pt-2">
            <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-800/60 border border-slate-700/60">
              <Building2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-xs text-white">Multi-Company Architecture</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Effortlessly switch between multiple GSTINs and legal entities with complete ledger and bank isolation.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-800/60 border border-slate-700/60">
              <Lock className="w-5 h-5 text-teal-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-xs text-white">Role-Based Credential Security</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Granular permission enforcement across Business Owners, Finance Managers, Accountants, and Statutory Auditors.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Login Card & Quick Credentials */}
        <div className="lg:col-span-7 space-y-6">
          {/* Sign In Card */}
          <div className="bg-white rounded-2xl shadow-2xl p-6 sm:p-8 text-slate-900 border border-slate-200 relative overflow-hidden">
            <div className="mb-6">
              <h2 className="text-xl font-bold text-slate-900">Sign In to Your Account</h2>
              <p className="text-xs text-slate-500 mt-1">
                Enter your unique User ID and Password to access your assigned companies
              </p>
            </div>

            {/* Error Message */}
            {errorMessage && (
              <div className="mb-4 p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-2.5 text-xs font-semibold text-rose-800 animate-in fade-in duration-100">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Success / Pre-fill Notice */}
            {successNotice && (
              <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-2.5 text-xs font-semibold text-emerald-800 animate-in fade-in duration-100">
                <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{successNotice}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* User ID / Email */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1.5">
                  User ID or Registered Email
                </label>
                <div className="relative">
                  <UserIcon className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    required
                    value={userIdInput}
                    onChange={(e) => {
                      setUserIdInput(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                      if (successNotice) setSuccessNotice(null);
                    }}
                    placeholder="e.g. dimple.admin (or type 'admin') or rohan.acc"
                    className="w-full pl-9 pr-3 py-2.5 text-xs font-semibold text-slate-900 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 transition-colors"
                  />
                </div>
                <p className="text-[10px] text-slate-500 mt-1">
                  Tip: You can enter <strong className="text-slate-700">dimple.admin</strong>, or shorthand <strong className="text-slate-700">admin</strong>, <strong className="text-slate-700">rohan</strong>, <strong className="text-slate-700">ananya</strong>, <strong className="text-slate-700">vikram</strong>, <strong className="text-slate-700">suresh</strong>.
                </p>
              </div>

              {/* Password */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-bold text-slate-700">
                    Password
                  </label>
                  <span className="text-[11px] text-emerald-700 font-semibold cursor-pointer hover:underline" onClick={() => handleQuickLogin('dimple.admin', 'Admin@2026')}>
                    Default admin: Admin@2026
                  </span>
                </div>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={passwordInput}
                    onChange={(e) => {
                      setPasswordInput(e.target.value);
                      if (errorMessage) setErrorMessage(null);
                      if (successNotice) setSuccessNotice(null);
                    }}
                    placeholder="Enter password (e.g. Admin@2026)"
                    className="w-full pl-9 pr-10 py-2.5 text-xs font-semibold text-slate-900 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 active:scale-[0.99] rounded-xl transition-all shadow-md flex items-center justify-center gap-2 cursor-pointer mt-2"
              >
                {isLoading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <span>Verify & Sign In</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Quick Access Demo Credential Cards */}
          <div className="bg-slate-800/80 backdrop-blur-md rounded-2xl p-5 border border-slate-700/80 shadow-xl">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                  Test Accounts & User ID Credentials
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleResetAccounts}
                  title="Reset test accounts to factory defaults"
                  className="text-[10px] font-semibold text-emerald-300 hover:text-white bg-slate-700/60 hover:bg-slate-700 px-2 py-1 rounded-md border border-slate-600 flex items-center gap-1 transition-colors"
                >
                  <RotateCcw className="w-3 h-3 text-emerald-400" />
                  <span>Reset Test Accounts</span>
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {DEMO_USERS.map((usr) => {
                const pass = usr.password || 'Admin@2026';
                return (
                  <div
                    key={usr.id}
                    onClick={() => handleQuickLogin(usr.userId || usr.email, pass)}
                    className="p-3 rounded-xl bg-slate-900/60 hover:bg-emerald-950/40 border border-slate-700/60 hover:border-emerald-500/50 transition-all cursor-pointer group flex flex-col justify-between"
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <div>
                        <p className="text-xs font-bold text-white group-hover:text-emerald-300 transition-colors">
                          {usr.name}
                        </p>
                        <span className="text-[10px] font-semibold text-emerald-400">
                          {usr.role}
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={(e) => handleFillOnly(usr.userId, pass, e)}
                          title="Pre-fill credentials into the input fields above"
                          className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
                        >
                          Fill
                        </button>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                          Sign In →
                        </span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between font-mono">
                      <span>ID: <strong className="text-slate-200">{usr.userId}</strong></span>
                      <span>Pass: <strong className="text-slate-200">{pass}</strong></span>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-3 pt-3 border-t border-slate-700/50 flex items-center justify-between text-[11px] text-slate-400">
              <span>All test accounts also accept default master password: <strong className="text-emerald-300 font-mono">Admin@2026</strong></span>
              <span className="text-slate-500 hidden md:inline">Click card to sign in</span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="max-w-6xl w-full mx-auto pt-4 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
        <p>© 2026 FinRecon India. Compliant with ICAI Standards on Auditing & IT Act 2000.</p>
        <p className="text-[11px]">Financial Year: FY 2026-27 | Assessment Year: AY 2027-28</p>
      </div>
    </div>
  );
};
