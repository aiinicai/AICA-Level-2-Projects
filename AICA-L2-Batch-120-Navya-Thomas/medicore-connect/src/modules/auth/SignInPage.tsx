import React, { useState } from 'react';
import { Eye, EyeOff, Lock, User as UserIcon, CheckCircle, ArrowRight, ShieldCheck } from 'lucide-react';
import { USERS, findUserById } from '../../data/users';
import { setActiveUser } from '../../core/auth';
import { User } from '../../core/types';

interface SignInPageProps {
  onSuccess: () => void;
}

export const SignInPage: React.FC<SignInPageProps> = ({ onSuccess }) => {
  const [userId, setUserId] = useState('charlotte.davis');
  const [password, setPassword] = useState('Charlotte@2026');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const user = findUserById(userId);
    if (!user || user.password !== password) {
      setError('Invalid User ID or password. Please verify your credentials or click a demo account below.');
      return;
    }

    setActiveUser(user);
    onSuccess();
  };

  const autofillUser = (u: User) => {
    setUserId(u.userId);
    setPassword(u.password || '');
    setError('');
  };

  return (
    <div className="min-h-screen flex bg-gray-50 select-none">
      {/* Left Split: Plum Brand Showcase */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-[#3F1D5C] via-[#5B2C83] to-[#29103e] text-white p-12 flex-col justify-between relative overflow-hidden">
        {/* Subtle geometric pattern */}
        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#EDE4F5_1px,transparent_1px)] [background-size:20px_20px] pointer-events-none" />
        <div className="absolute -bottom-20 -left-20 w-80 h-80 rounded-full bg-amber-400/10 blur-3xl pointer-events-none" />

        {/* Brand Header */}
        <div className="relative z-10 flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#844db3] to-[#5B2C83] border border-plum-300/40 flex items-center justify-center shadow-lg">
            <svg viewBox="0 0 24 24" className="w-6 h-6 text-amber-300 fill-current">
              <polygon points="12,2 21,7.5 21,16.5 12,22 3,16.5 3,7.5" fill="none" stroke="currentColor" strokeWidth="2" />
              <path d="M12 7v10M7 12h10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-extrabold tracking-tight">
              MediCore <span className="font-light text-plum-200">Connect</span>
            </h1>
            <p className="text-[11px] text-plum-300 tracking-wider uppercase font-semibold">
              Healthcare Financials & Supply Chain ERP
            </p>
          </div>
        </div>

        {/* Narrative text */}
        <div className="relative z-10 my-auto max-w-lg">
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-400/20 text-amber-300 border border-amber-400/30 mb-4">
            Oracle Fusion Cloud Architecture
          </span>
          <h2 className="text-3xl font-extrabold tracking-tight leading-snug">
            Enterprise Financial Rigour for Meridian Healthcare Group
          </h2>
          <p className="mt-4 text-plum-100 text-sm leading-relaxed">
            Unifying 5 Hospitals, 5 Clinics, and 5 Pharmacies across the UAE. End-to-end Maker–Checker governance, strict subledger-to-GL double-entry accounting, and real-time IFRS financial reporting.
          </p>

          <div className="grid grid-cols-2 gap-4 mt-8">
            <div className="bg-white/10 rounded-lg p-3 border border-white/10">
              <span className="text-amber-300 font-bold text-lg block">15 Units</span>
              <span className="text-xs text-plum-200">Balancing GL Segments</span>
            </div>
            <div className="bg-white/10 rounded-lg p-3 border border-white/10">
              <span className="text-emerald-300 font-bold text-lg block">AED Exact</span>
              <span className="text-xs text-plum-200">Zero Floating-Point Error</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="relative z-10 text-xs text-plum-300 flex items-center justify-between">
          <span>&copy; 2026 Meridian Healthcare Group</span>
          <span>Fiscal Calendar: Calendar Year (AED)</span>
        </div>
      </div>

      {/* Right Split: Sign In Form + Demo Helpers */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-12 overflow-y-auto">
        <div className="w-full max-w-md">
          {/* Mobile brand header */}
          <div className="lg:hidden flex items-center space-x-2.5 mb-6">
            <div className="w-8 h-8 rounded-lg bg-[#5B2C83] flex items-center justify-center">
              <svg viewBox="0 0 24 24" className="w-5 h-5 text-amber-300 fill-current">
                <polygon points="12,2 21,7.5 21,16.5 12,22 3,16.5 3,7.5" fill="none" stroke="currentColor" strokeWidth="2" />
                <path d="M12 7v10M7 12h10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
              </svg>
            </div>
            <span className="font-bold text-base text-[#3F1D5C]">MediCore Connect</span>
          </div>

          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-900">Sign In</h2>
            <p className="text-xs text-gray-500 mt-1">
              Enter your corporate credentials to access the ERP workspace.
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center space-x-2">
              <span className="font-bold">Error:</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                User ID
              </label>
              <div className="relative">
                <UserIcon className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  required
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  placeholder="e.g. charlotte.davis"
                  className="w-full pl-9 pr-3 py-2 bg-white border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-[#5B2C83] focus:border-[#5B2C83]"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-10 py-2 bg-white border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-[#5B2C83] focus:border-[#5B2C83]"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-2.5 px-4 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white font-semibold text-xs rounded-lg shadow-md transition-colors flex items-center justify-center space-x-2 cursor-pointer"
            >
              <span>Sign In to ERP</span>
              <ArrowRight className="w-4 h-4 text-amber-300" />
            </button>
          </form>

          {/* Demo Credentials Helper Box */}
          <div className="mt-6 pt-5 border-t border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-[#5B2C83] uppercase tracking-wider">
                Demo Credentials (Click to Autofill)
              </span>
              <span className="text-[10px] text-gray-400">Section 3 Spec</span>
            </div>
            <p className="text-[11px] text-gray-500 mb-2.5">
              Click any account below to autofill and evaluate maker-checker roles and approval limits:
            </p>

            <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
              {USERS.map((u) => {
                const isSelected = userId === u.userId;
                return (
                  <button
                    key={u.userId}
                    type="button"
                    onClick={() => autofillUser(u)}
                    className={`w-full text-left p-2 rounded-lg border text-xs flex items-center justify-between transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-plum-50 border-[#5B2C83] text-[#3F1D5C] font-semibold'
                        : 'bg-white hover:bg-gray-50 border-gray-200 text-gray-700'
                    }`}
                  >
                    <div>
                      <div className="font-semibold text-gray-900">{u.name}</div>
                      <div className="text-[10px] text-gray-500">
                        {u.userId === 'charlotte.davis'
                          ? 'Maker (GL) & Approver (AP, AR, Cash, SCE)'
                          : u.userId === 'daniel.reed'
                          ? 'CFO & Approver (Procurement, FA, IC, GL)'
                          : u.userId === 'noah.bennett'
                          ? 'Store Controller (SCE Maker)'
                          : u.userId === 'emma.collins'
                          ? 'Intercompany Accountant (IC Maker)'
                          : u.role}{' '}
                        &bull; <span className="font-mono text-[#5B2C83]">{u.userId}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 font-medium block">
                        {u.approvalLimitAED ? `AED ${u.approvalLimitAED.toLocaleString()}` : u.approvalLimitAED === null ? 'Unlimited' : 'Maker Only'}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
