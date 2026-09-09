import React, { useState } from 'react';
import {
  ShieldCheck,
  Lock,
  User,
  Mail,
  UserCheck,
  AlertCircle,
  CheckCircle2,
  Building2,
  KeyRound,
  Eye,
  EyeOff,
  Sparkles,
} from 'lucide-react';
import { AppUser, UserRole } from '../types/accounting';
import { authService } from '../utils/authService';

interface LoginScreenProps {
  onLoginSuccess: (user: AppUser) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
  const [activeTab, setActiveTab] = useState<'LOGIN' | 'REGISTER'>('LOGIN');
  
  // Login Form
  const [loginId, setLoginId] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  
  // Register Form
  const [regId, setRegId] = useState('');
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regRole, setRegRole] = useState<UserRole>('AUDITOR');
  
  // States
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!loginId.trim() || !loginPassword) {
      setErrorMessage('Please enter both User ID and Password.');
      return;
    }

    setLoading(true);
    try {
      const res = await authService.login(loginId, loginPassword);
      if (res.success && res.user) {
        onLoginSuccess(res.user);
      } else {
        setErrorMessage(res.error || 'Login failed. Please check credentials.');
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!regId.trim() || !regName.trim() || !regPassword) {
      setErrorMessage('Please provide User ID, Full Name, and Password.');
      return;
    }

    if (regPassword.length < 5) {
      setErrorMessage('Password must be at least 5 characters long.');
      return;
    }

    setLoading(true);
    try {
      const res = await authService.register({
        id: regId.trim(),
        name: regName.trim(),
        email: regEmail.trim(),
        password: regPassword,
        role: regRole,
      });

      if (res.success) {
        setSuccessMessage(
          res.message || 'Registration submitted! The Administrator must approve your User ID before you can log in.'
        );
        setRegId('');
        setRegName('');
        setRegEmail('');
        setRegPassword('');
      } else {
        setErrorMessage(res.error || 'Registration failed.');
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'An error occurred during registration.');
    } finally {
      setLoading(false);
    }
  };

  const quickFillCredentials = (id: string, pass: string) => {
    setLoginId(id);
    setLoginPassword(pass);
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3] flex flex-col justify-center items-center p-4 selection:bg-[#238636] selection:text-white">
      {/* Background Subtle Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#161b22_1px,transparent_1px),linear-gradient(to_bottom,#161b22_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none opacity-40" />

      <div className="w-full max-w-md z-10">
        {/* Header Branding */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center p-3 bg-[#161b22] border border-[#30363d] rounded-lg shadow-md mb-3">
            <Building2 className="w-8 h-8 text-[#58a6ff]" />
          </div>
          <h1 className="text-xl font-bold font-serif tracking-tight text-white">
            ICAI Non-Corporate Reporting Portal
          </h1>
          <p className="text-xs text-[#8b949e] mt-1 font-mono">
            Balance Sheet, P&L & Working Papers Workstation
          </p>
        </div>

        {/* Card */}
        <div className="bg-[#161b22] border border-[#30363d] rounded-md shadow-2xl overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b border-[#30363d] bg-[#0d1117]/60">
            <button
              onClick={() => {
                setActiveTab('LOGIN');
                setErrorMessage(null);
                setSuccessMessage(null);
              }}
              className={`flex-1 py-3 text-xs font-mono font-semibold tracking-wider transition border-b-2 flex items-center justify-center gap-1.5 ${
                activeTab === 'LOGIN'
                  ? 'border-[#58a6ff] text-[#58a6ff] bg-[#161b22]'
                  : 'border-transparent text-[#8b949e] hover:text-white'
              }`}
              id="tab-btn-signin"
            >
              <Lock className="w-3.5 h-3.5" />
              SIGN IN
            </button>
            <button
              onClick={() => {
                setActiveTab('REGISTER');
                setErrorMessage(null);
                setSuccessMessage(null);
              }}
              className={`flex-1 py-3 text-xs font-mono font-semibold tracking-wider transition border-b-2 flex items-center justify-center gap-1.5 ${
                activeTab === 'REGISTER'
                  ? 'border-[#58a6ff] text-[#58a6ff] bg-[#161b22]'
                  : 'border-transparent text-[#8b949e] hover:text-white'
              }`}
              id="tab-btn-register"
            >
              <UserCheck className="w-3.5 h-3.5" />
              REQUEST USER ID
            </button>
          </div>

          {/* Feedback Alerts */}
          <div className="p-6 pb-2">
            {errorMessage && (
              <div className="mb-4 p-3 bg-[#3d1d1d] border border-[#f85149]/40 text-[#ff7b72] text-xs font-mono rounded flex items-start gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <div>{errorMessage}</div>
              </div>
            )}

            {successMessage && (
              <div className="mb-4 p-3 bg-[#1c3321] border border-[#3fb950]/40 text-[#7ee787] text-xs font-mono rounded flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                <div>{successMessage}</div>
              </div>
            )}
          </div>

          {/* Tab 1: Login Form */}
          {activeTab === 'LOGIN' && (
            <form onSubmit={handleLogin} className="px-6 pb-6 space-y-4">
              <div>
                <label className="block text-[11px] font-mono uppercase text-[#8b949e] mb-1.5">
                  User ID / Username
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#8b949e]">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    value={loginId}
                    onChange={(e) => setLoginId(e.target.value)}
                    placeholder="e.g. admin or auditor"
                    required
                    className="w-full pl-9 pr-3 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white placeholder-[#484f58] focus:border-[#58a6ff] focus:outline-none focus:ring-1 focus:ring-[#58a6ff] font-mono"
                    id="input-login-userid"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-mono uppercase text-[#8b949e] mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#8b949e]">
                    <KeyRound className="w-4 h-4" />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full pl-9 pr-10 py-2 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white placeholder-[#484f58] focus:border-[#58a6ff] focus:outline-none focus:ring-1 focus:ring-[#58a6ff] font-mono"
                    id="input-login-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-[#8b949e] hover:text-white"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 bg-[#238636] hover:bg-[#2ea043] text-white font-mono text-xs font-bold uppercase tracking-wider rounded transition disabled:opacity-50 flex items-center justify-center gap-2 mt-2 shadow-sm"
                id="btn-submit-login"
              >
                <ShieldCheck className="w-4 h-4" />
                {loading ? 'AUTHENTICATING...' : 'ACCESS PORTAL'}
              </button>

              {/* Quick Demo Credentials Box */}
              <div className="mt-5 pt-4 border-t border-[#30363d]">
                <p className="text-[10.5px] font-mono text-[#8b949e] mb-2 text-center">
                  Quick Access Demo Accounts (Click to Fill):
                </p>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => quickFillCredentials('admin', 'Admin@123')}
                    className="p-2 bg-[#0d1117] hover:bg-[#21262d] border border-[#30363d] hover:border-[#58a6ff]/50 rounded text-left transition"
                    id="btn-quick-admin"
                  >
                    <div className="text-[10px] font-mono font-bold text-[#58a6ff]">ADMIN ROLE</div>
                    <div className="text-[11px] font-mono text-[#e6edf3]">admin</div>
                    <div className="text-[9px] font-mono text-[#8b949e]">Pass: Admin@123</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => quickFillCredentials('auditor', 'Audit@123')}
                    className="p-2 bg-[#0d1117] hover:bg-[#21262d] border border-[#30363d] hover:border-[#3fb950]/50 rounded text-left transition"
                    id="btn-quick-auditor"
                  >
                    <div className="text-[10px] font-mono font-bold text-[#3fb950]">AUDITOR ROLE</div>
                    <div className="text-[11px] font-mono text-[#e6edf3]">auditor</div>
                    <div className="text-[9px] font-mono text-[#8b949e]">Pass: Audit@123</div>
                  </button>
                </div>
              </div>
            </form>
          )}

          {/* Tab 2: Request User ID (Registration with Admin Approval) */}
          {activeTab === 'REGISTER' && (
            <form onSubmit={handleRegister} className="px-6 pb-6 space-y-3.5">
              <div className="bg-[#1f242c] p-2.5 rounded border border-[#30363d] text-[11px] font-mono text-[#8b949e] flex items-start gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-[#d29922] shrink-0 mt-0.5" />
                <span>
                  New accounts require Administrator authorization. You will receive an approval confirmation once authorized by the CA Firm Admin.
                </span>
              </div>

              <div>
                <label className="block text-[11px] font-mono uppercase text-[#8b949e] mb-1">
                  Desired User ID *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#8b949e]">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    value={regId}
                    onChange={(e) => setRegId(e.target.value.toLowerCase().replace(/[^a-z0-9._-]/g, ''))}
                    placeholder="e.g. priyanka.garg"
                    required
                    className="w-full pl-9 pr-3 py-1.5 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white placeholder-[#484f58] focus:border-[#58a6ff] focus:outline-none font-mono"
                    id="input-reg-userid"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-mono uppercase text-[#8b949e] mb-1">
                  Full Name *
                </label>
                <input
                  type="text"
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                  placeholder="e.g. CA Priyanka Garg"
                  required
                  className="w-full px-3 py-1.5 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white placeholder-[#484f58] focus:border-[#58a6ff] focus:outline-none font-mono"
                  id="input-reg-name"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono uppercase text-[#8b949e] mb-1">
                  Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#8b949e]">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    type="email"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="name@firm.com"
                    className="w-full pl-9 pr-3 py-1.5 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white placeholder-[#484f58] focus:border-[#58a6ff] focus:outline-none font-mono"
                    id="input-reg-email"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-mono uppercase text-[#8b949e] mb-1">
                  Password *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#8b949e]">
                    <KeyRound className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    placeholder="At least 5 characters"
                    required
                    className="w-full pl-9 pr-3 py-1.5 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white placeholder-[#484f58] focus:border-[#58a6ff] focus:outline-none font-mono"
                    id="input-reg-password"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-mono uppercase text-[#8b949e] mb-1">
                  Requested Role
                </label>
                <select
                  value={regRole}
                  onChange={(e) => setRegRole(e.target.value as UserRole)}
                  className="w-full px-3 py-1.5 bg-[#0d1117] border border-[#30363d] rounded text-sm text-white focus:border-[#58a6ff] focus:outline-none font-mono"
                  id="select-reg-role"
                >
                  <option value="AUDITOR">Auditor / Reviewer</option>
                  <option value="ACCOUNTANT">Accountant / Staff</option>
                  <option value="ADMIN">Firm Administrator</option>
                  <option value="VIEWER">Read-Only Viewer</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 bg-[#1f6feb] hover:bg-[#388bfd] text-white font-mono text-xs font-bold uppercase tracking-wider rounded transition disabled:opacity-50 flex items-center justify-center gap-2 mt-3 shadow-sm"
                id="btn-submit-register"
              >
                <UserCheck className="w-4 h-4" />
                {loading ? 'SUBMITTING...' : 'SUBMIT REQUEST FOR APPROVAL'}
              </button>
            </form>
          )}
        </div>

        {/* Footer info */}
        <div className="text-center mt-4 text-[10.5px] font-mono text-[#8b949e]">
          Protected by Role-Based Access Control & ICAI Compliance Shield
        </div>
      </div>
    </div>
  );
};
