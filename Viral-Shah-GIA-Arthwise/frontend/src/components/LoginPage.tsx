import React, { useState } from 'react';
import { Building2, Lock, User, Eye, EyeOff, ShieldCheck, ArrowRight, Sparkles, CheckCircle2 } from 'lucide-react';
import { ApiClient } from '../api/client';
import { UserRole, CompanyProfile } from '../types';

interface LoginPageProps {
  onLoginSuccess: (token: string, user: { id: string; email: string; full_name: string; role: UserRole }) => void;
  activeCompany?: CompanyProfile | null;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess, activeCompany }) => {
  const [username, setUsername] = useState('analyst@giaarthwise.com');
  const [password, setPassword] = useState('Analyst@123');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMessage('Please enter both username/email and password.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await ApiClient.request<{ access_token: string; user: { id: string; email: string; full_name: string; role: UserRole } }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: username.trim(), password: password.trim() }),
      });

      ApiClient.setToken(res.access_token);
      onLoginSuccess(res.access_token, res.user);
    } catch (err: any) {
      setErrorMessage(err.message || 'Invalid username or password. Please verify credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickFill = (email: string, pass: string) => {
    setUsername(email);
    setPassword(pass);
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen bg-[#1b2632] flex flex-col justify-center items-center px-4 py-8 relative overflow-hidden font-sans">
      {/* Decorative Brand Accent Background Glows */}
      <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-[#a45139]/20 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-32 -right-32 w-96 h-96 rounded-full bg-[#243343]/60 blur-3xl pointer-events-none" />

      {/* Main Login Card */}
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden relative z-10 animate-in fade-in zoom-in-95 duration-200">
        
        {/* Top Header Strip with Corporate Colors */}
        <div className="bg-[#1b2632] text-white p-6 pb-7 border-b border-[#2a3c4f] relative">
          <div className="flex items-center gap-3">
            {activeCompany?.logo_data ? (
              <div className="w-12 h-12 rounded-xl bg-white flex items-center justify-center shadow-lg border border-slate-200 overflow-hidden p-1">
                <img
                  src={activeCompany.logo_data}
                  alt={activeCompany.brand_name}
                  className="w-full h-full object-contain"
                />
              </div>
            ) : (
              <div className="w-12 h-12 rounded-xl bg-[#a45139] text-white flex items-center justify-center shadow-lg border border-[#ebb9ab]/30">
                <Building2 className="w-6 h-6" />
              </div>
            )}
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-black tracking-tight text-white">
                  {activeCompany?.brand_name || 'GIA_Arthwise'}
                </h1>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-[#a45139] text-white">
                  v1.0
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-0.5 font-medium">
                {activeCompany?.tagline || 'Loan Proposal Evaluation & Debt Syndication'}
              </p>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-700/60 flex items-center justify-between text-[11px] text-slate-300">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-[#a45139]" />
              Institutional Banking & CMA Engine
            </span>
            <span className="font-mono text-slate-400">DPDP Compliant</span>
          </div>
        </div>

        {/* Form Body */}
        <div className="p-6 sm:p-7">
          <div className="mb-5">
            <h2 className="text-lg font-bold text-[#1b2632]">Sign In to Platform</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Enter your credentials to access the syndication pipeline & proposals.
            </p>
          </div>

          {errorMessage && (
            <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-start gap-2">
              <span className="font-bold text-rose-700">Error:</span>
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Username or Email ID
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="text"
                  autoFocus
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. analyst@giaarthwise.com or analyst"
                  className="w-full pl-9 pr-3 py-2.5 text-xs bg-slate-50 border border-slate-300 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#a45139] focus:bg-white transition-all font-medium"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-bold text-slate-700">
                  Password
                </label>
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full pl-9 pr-10 py-2.5 text-xs bg-slate-50 border border-slate-300 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#a45139] focus:bg-white transition-all font-medium"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 transition-colors p-0.5"
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 py-2.5 px-4 rounded-lg bg-[#a45139] hover:bg-[#863e2a] text-white text-xs font-bold shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
            >
              <span>{isLoading ? 'Verifying & Opening Pipeline...' : 'Sign In & Open Proposals'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Quick-Select Credentials Panel */}
          <div className="mt-6 pt-5 border-t border-slate-100">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                1-Click Quick Credentials:
              </span>
              <span className="text-[10px] text-slate-400">Click to fill</span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <button
                type="button"
                onClick={() => handleQuickFill('analyst@giaarthwise.com', 'Analyst@123')}
                className={`p-2 rounded-lg border text-left transition-all ${
                  username.includes('analyst')
                    ? 'border-[#a45139] bg-[#faece7] text-[#1b2632] font-semibold'
                    : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100'
                }`}
              >
                <div className="font-bold text-[#1b2632]">Senior Analyst</div>
                <div className="text-[10px] text-slate-500 font-mono">analyst@giaarthwise.com</div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickFill('reviewer@giaarthwise.com', 'Reviewer@123')}
                className={`p-2 rounded-lg border text-left transition-all ${
                  username.includes('reviewer')
                    ? 'border-[#a45139] bg-[#faece7] text-[#1b2632] font-semibold'
                    : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100'
                }`}
              >
                <div className="font-bold text-[#1b2632]">Credit Reviewer</div>
                <div className="text-[10px] text-slate-500 font-mono">reviewer@giaarthwise.com</div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickFill('admin@giaarthwise.com', 'Admin@123')}
                className={`p-2 rounded-lg border text-left transition-all ${
                  username.includes('admin')
                    ? 'border-[#a45139] bg-[#faece7] text-[#1b2632] font-semibold'
                    : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100'
                }`}
              >
                <div className="font-bold text-[#1b2632]">Administrator</div>
                <div className="text-[10px] text-slate-500 font-mono">admin@giaarthwise.com</div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickFill('client@giaarthwise.com', 'Client@123')}
                className={`p-2 rounded-lg border text-left transition-all ${
                  username.includes('client')
                    ? 'border-[#a45139] bg-[#faece7] text-[#1b2632] font-semibold'
                    : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100'
                }`}
              >
                <div className="font-bold text-[#1b2632]">Borrower Client</div>
                <div className="text-[10px] text-slate-500 font-mono">client@giaarthwise.com</div>
              </button>
            </div>
          </div>

          {/* Color Palette Indicator as requested */}
          <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400 font-mono">
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-[#1b2632] border border-slate-300" />
              #1b2632 (C84 M72 Y54 K62)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-[#a45139] border border-slate-300" />
              #a45139 (C26 M76 Y82 K17)
            </span>
          </div>
        </div>
      </div>

      {/* Footer Notice */}
      <p className="mt-6 text-xs text-slate-400 text-center max-w-sm leading-relaxed">
        <strong>Preliminary Credit Appraisal Engine</strong> • All calculations and eligibility limits are for professional underwriting review.
      </p>
    </div>
  );
};
