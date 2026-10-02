import React, { useState } from 'react';
import {
  Lock,
  User,
  ShieldCheck,
  ArrowRight,
  FileCheck2,
  Eye,
  EyeOff,
  Sparkles,
  Database,
  CheckCircle2,
  KeyRound,
  AlertCircle,
  ArrowLeft
} from 'lucide-react';
import { User as UserType } from '../types';
import { systemService } from '../lib/services/systemService';

interface LoginScreenProps {
  onLoginSuccess: (user: UserType) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
  // Start empty so user clicks a role or enters credentials, then clicks Sign In to Portal
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [selectedRole, setSelectedRole] = useState<'Admin' | 'User' | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Change Password, right from the login page - lets someone update the
  // admin or demo password before they've signed in, so long as they can
  // prove they already know the CURRENT one (same rule as the in-app
  // Settings > Login & Security page). There's no "forgot password, reset
  // via email" flow here, since this is a local demo app with no real
  // backend to send a reset link through - requiring the current password
  // is the honest substitute, and it's still useful for "I want to change
  // my password before I even sign in" without going through Settings.
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [cpTarget, setCpTarget] = useState<'admin' | 'demo'>('admin');
  const [cpCurrentPassword, setCpCurrentPassword] = useState('');
  const [cpNewPassword, setCpNewPassword] = useState('');
  const [cpConfirmPassword, setCpConfirmPassword] = useState('');
  const [cpSaving, setCpSaving] = useState(false);
  const [cpError, setCpError] = useState('');
  const [cpSuccess, setCpSuccess] = useState('');

  const resetChangePasswordForm = () => {
    setCpCurrentPassword('');
    setCpNewPassword('');
    setCpConfirmPassword('');
    setCpError('');
    setCpSuccess('');
  };

  const handleOpenChangePassword = () => {
    resetChangePasswordForm();
    setShowChangePassword(true);
  };

  const handleBackToSignIn = () => {
    resetChangePasswordForm();
    setShowChangePassword(false);
  };

  const handleChangePassword = (e: React.FormEvent) => {
    e.preventDefault();
    setCpError('');
    setCpSuccess('');

    if (cpNewPassword !== cpConfirmPassword) {
      setCpError('New password and confirmation do not match.');
      return;
    }

    setCpSaving(true);
    try {
      systemService.changeLoginPassword(cpTarget, cpCurrentPassword, cpNewPassword);
      setCpSuccess(
        `Password updated for the ${cpTarget === 'admin' ? 'Admin' : 'User (demo)'} account. You can sign in with it now.`
      );
      setCpCurrentPassword('');
      setCpNewPassword('');
      setCpConfirmPassword('');
    } catch (err: any) {
      setCpError(err.message || 'Failed to change password.');
    } finally {
      setCpSaving(false);
    }
  };

  const handleLogin = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMsg('Please select a role button below or enter username and password.');
      return;
    }

    setLoading(true);
    setErrorMsg('');

    try {
      const user = systemService.authenticateUser(username, password);
      onLoginSuccess(user);
    } catch (err: any) {
      setErrorMsg(err.message || 'Authentication failed. Please verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  // Passwords are configurable (Settings > Login & Security), so the
  // 1-click role buttons and the on-screen hint below read the CURRENT
  // password from settings each time rather than a hardcoded default -
  // otherwise this convenience would quietly stop working, or worse, show
  // a stale password, the moment someone changes it.
  const currentSettings = systemService.getSettings();

  // When clicking Admin Role or User Role buttons, populate the distinct username & password into the input fields and show role badge
  const handleSelectRole = (role: 'Admin' | 'User') => {
    setSelectedRole(role);
    setErrorMsg('');
    if (role === 'Admin') {
      setUsername('admin');
      setPassword(currentSettings.adminPassword);
    } else {
      setUsername('demo');
      setPassword(currentSettings.userPassword);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden select-none">
      {/* Decorative background glows */}
      <div className="absolute top-10 left-1/4 w-96 h-96 bg-blue-600/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 right-1/4 w-96 h-96 bg-indigo-600/15 rounded-full blur-3xl pointer-events-none" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10 text-center space-y-3">
        {/* Brand Logo & Icon */}
        <div className="inline-flex p-3.5 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 text-white shadow-xl shadow-blue-500/25 ring-1 ring-white/20">
          <FileCheck2 className="w-8 h-8" />
        </div>
        
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            FinTech Billing Portal
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Quarterly Delivery Logs &amp; Automated Invoice System
          </p>
        </div>

        {/* Workflow indicator tag */}
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700/60 text-slate-300 text-xs font-medium">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span>Access Protected: Sign In Required</span>
        </div>
      </div>

      <div className="mt-7 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="bg-white/95 backdrop-blur-md py-8 px-6 sm:px-10 shadow-2xl rounded-2xl border border-slate-100/20 text-slate-800 space-y-5">
          {showChangePassword ? (
            <>
              {/* Change Password Panel - reachable from the login page
                  itself, before signing in. Still requires the CURRENT
                  password as proof of identity (there's no email-based
                  reset in this local demo app), so it's a genuine
                  self-service change, not an open door to reset anyone's
                  password without knowing it. */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <KeyRound className="w-4 h-4 text-blue-600" />
                  <h2 className="text-sm font-bold text-slate-800">Change Password</h2>
                </div>
                <button
                  type="button"
                  onClick={handleBackToSignIn}
                  className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 font-semibold"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to Sign In</span>
                </button>
              </div>

              <form className="space-y-4" onSubmit={handleChangePassword}>
                {cpError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg font-medium flex items-start gap-2">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                    <span>{cpError}</span>
                  </div>
                )}
                {cpSuccess && (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs rounded-lg font-medium flex items-start gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                    <span>{cpSuccess}</span>
                  </div>
                )}

                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                    Account
                  </label>
                  <div className="grid grid-cols-2 gap-2.5">
                    <button
                      type="button"
                      onClick={() => setCpTarget('admin')}
                      className={`flex items-center justify-center gap-1.5 p-2.5 rounded-xl border text-xs font-bold transition ${
                        cpTarget === 'admin'
                          ? 'border-blue-600 bg-blue-50/90 text-blue-700 ring-2 ring-blue-500/20'
                          : 'border-slate-200 bg-slate-50/80 text-slate-600 hover:bg-blue-50/50 hover:border-blue-300'
                      }`}
                    >
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>Admin</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setCpTarget('demo')}
                      className={`flex items-center justify-center gap-1.5 p-2.5 rounded-xl border text-xs font-bold transition ${
                        cpTarget === 'demo'
                          ? 'border-indigo-600 bg-indigo-50/90 text-indigo-700 ring-2 ring-indigo-500/20'
                          : 'border-slate-200 bg-slate-50/80 text-slate-600 hover:bg-indigo-50/50 hover:border-indigo-300'
                      }`}
                    >
                      <User className="w-3.5 h-3.5" />
                      <span>User (demo)</span>
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                    Current Password
                  </label>
                  <div className="relative">
                    <Lock className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                    <input
                      type="password"
                      required
                      value={cpCurrentPassword}
                      onChange={(e) => setCpCurrentPassword(e.target.value)}
                      className="w-full pl-9 pr-3 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-900 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none transition"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                      New Password
                    </label>
                    <input
                      type="password"
                      required
                      minLength={4}
                      value={cpNewPassword}
                      onChange={(e) => setCpNewPassword(e.target.value)}
                      className="w-full px-3 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-900 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none transition"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                      Confirm New Password
                    </label>
                    <input
                      type="password"
                      required
                      minLength={4}
                      value={cpConfirmPassword}
                      onChange={(e) => setCpConfirmPassword(e.target.value)}
                      className="w-full px-3 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-900 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none transition"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={cpSaving}
                  className="w-full mt-2 flex items-center justify-center gap-2 py-3 px-4 rounded-lg shadow-md shadow-blue-500/20 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 active:scale-[0.99] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition cursor-pointer disabled:opacity-50"
                >
                  <KeyRound className="w-4 h-4" />
                  <span>{cpSaving ? 'Updating...' : 'Update Password'}</span>
                </button>
              </form>
            </>
          ) : (
          <>
          {/* Role Selection Buttons at Top */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                Select User Role to Load Credentials
              </span>
              {selectedRole && (
                <span className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> {selectedRole} Credentials Loaded
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <button
                type="button"
                onClick={() => handleSelectRole('Admin')}
                className={`flex flex-col items-start p-3 rounded-xl border text-left cursor-pointer transition relative ${
                  selectedRole === 'Admin'
                    ? 'border-blue-600 bg-blue-50/90 shadow-sm ring-2 ring-blue-500/20'
                    : 'border-slate-200 bg-slate-50/80 hover:bg-blue-50/50 hover:border-blue-300'
                }`}
              >
                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800">
                  <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
                  <span>Admin Role</span>
                </div>
                <div className="text-[11px] font-mono text-blue-700 font-semibold mt-1">
                  admin
                </div>
                <span className="text-[10px] text-slate-500">
                  Full admin privileges
                </span>
              </button>

              <button
                type="button"
                onClick={() => handleSelectRole('User')}
                className={`flex flex-col items-start p-3 rounded-xl border text-left cursor-pointer transition relative ${
                  selectedRole === 'User'
                    ? 'border-indigo-600 bg-indigo-50/90 shadow-sm ring-2 ring-indigo-500/20'
                    : 'border-slate-200 bg-slate-50/80 hover:bg-indigo-50/50 hover:border-indigo-300'
                }`}
              >
                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800">
                  <User className="w-3.5 h-3.5 text-indigo-600" />
                  <span>User Role</span>
                </div>
                <div className="text-[11px] font-mono text-indigo-700 font-semibold mt-1">
                  demo
                </div>
                <span className="text-[10px] text-slate-500">
                  Standard operations
                </span>
              </button>
            </div>
          </div>

          <form className="space-y-4 pt-1" onSubmit={handleLogin}>
            {errorMsg && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg font-medium flex items-start gap-2">
                <span className="font-bold">Error:</span>
                <span>{errorMsg}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Username
              </label>
              <div className="relative">
                <User className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => {
                    setUsername(e.target.value);
                    setSelectedRole(null);
                  }}
                  placeholder="Click Admin Role / User Role above or enter username"
                  className="w-full pl-9 pr-3 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-900 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none transition font-medium"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Password
                </label>
                {selectedRole && (
                  <span className="text-[11px] text-emerald-600 font-semibold">
                    {selectedRole} password loaded
                  </span>
                )}
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    setSelectedRole(null);
                  }}
                  placeholder="Password"
                  className="w-full pl-9 pr-10 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-900 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 focus:outline-none"
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 flex items-center justify-center gap-2 py-3 px-4 rounded-lg shadow-md shadow-blue-500/20 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 active:scale-[0.99] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition cursor-pointer disabled:opacity-50"
            >
              <span>{loading ? 'Authenticating...' : 'Sign In to Portal'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="text-center">
            <button
              type="button"
              onClick={handleOpenChangePassword}
              className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-blue-600 font-semibold transition"
            >
              <KeyRound className="w-3.5 h-3.5" />
              <span>Change Password</span>
            </button>
          </div>

          {/* Quick System Highlights */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-[11px] text-slate-600 space-y-1.5">
            <div className="font-semibold text-slate-700 flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-blue-600" />
              <span>Full Prototype Workflow Included:</span>
            </div>
            <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[10px] text-slate-500">
              <div>• Excel Delivery Log Upload</div>
              <div>• Quarterly Billing Calculation</div>
              <div>• Client Confirmation Email</div>
              <div>• Automated Tax Invoice PDF</div>
              <div>• Full Audit Trail Log</div>
              <div>• SQLite DB Viewer (Admin)</div>
            </div>
          </div>
          </>
          )}
        </div>
      </div>
    </div>
  );
};
