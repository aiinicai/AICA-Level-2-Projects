import React, { useState, useEffect, useRef } from 'react';
import { login } from '../services/api';
import type { User } from '../types';
import { Lock, Mail, Sparkles, AlertCircle, CheckCircle, Loader } from 'lucide-react';

const HEALTH_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '') + '/health';
const MAX_RETRIES = 15;
const RETRY_INTERVAL_MS = 2000;

interface LoginPageProps {
  onLoginSuccess: (user: User) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [loginId, setLoginId] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Health check state
  const [apiReady, setApiReady] = useState(false);
  const [healthStatus, setHealthStatus] = useState<'checking' | 'ok' | 'failed'>('checking');
  const [retryCount, setRetryCount] = useState(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const checkHealth = async (attempt: number) => {
    try {
      const res = await fetch(HEALTH_URL, { signal: AbortSignal.timeout(3000) });
      if (res.ok) {
        setApiReady(true);
        setHealthStatus('ok');
        return;
      }
    } catch {
      // network error or timeout — keep retrying
    }
    if (attempt < MAX_RETRIES) {
      setRetryCount(attempt + 1);
      retryTimerRef.current = setTimeout(() => checkHealth(attempt + 1), RETRY_INTERVAL_MS);
    } else {
      setHealthStatus('failed');
    }
  };

  useEffect(() => {
    checkHealth(0);
    return () => {
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await login(loginId, password);
      onLoginSuccess(res.user);
    } catch (err: any) {
      if (err.message === 'Failed to fetch' || err.name === 'TypeError') {
        setError('Cannot reach the API server. Ensure the backend is running on http://127.0.0.1:8000.');
      } else {
        setError(err.message || 'Invalid Employee Code / Email or Password');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (empCode: string, pass: string) => {
    setLoginId(empCode);
    setPassword(pass);
    setLoading(true);
    setError(null);
    try {
      const res = await login(empCode, pass);
      onLoginSuccess(res.user);
    } catch (err: any) {
      if (err.message === 'Failed to fetch' || err.name === 'TypeError') {
        setError('Cannot reach the API server. Ensure the backend is running on http://127.0.0.1:8000.');
      } else {
        setError(err.message || 'Quick login failed');
      }
    } finally {
      setLoading(false);
    }
  };

  const buttonDisabled = loading || !apiReady;

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
      <div className="max-w-md w-full ca-card bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl space-y-6">
        {/* Header */}
        <div className="text-center space-y-2 pt-2">
          <div className="flex items-center justify-center gap-3">
            <div className="border-l-2 border-slate-300 dark:border-slate-700 pl-3 text-left">
              <span className="text-sm font-black tracking-widest text-[#1B365D] dark:text-blue-400 uppercase block leading-none">
                FS BUILDER LITE
              </span>
              <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 tracking-wider block mt-0.5">
                &nbsp;
              </span>
            </div>
          </div>

          <div className="inline-flex items-center gap-1.5 bg-orange-50 dark:bg-orange-950/60 border border-orange-200 dark:border-orange-900 px-3 py-1 rounded-full text-xs font-bold text-orange-700 dark:text-orange-300 mt-2">
            <Sparkles className="w-3.5 h-3.5" /> FS Builder Lite v0.2 Enterprise Portal
          </div>

          <p className="text-xs text-ca-muted pt-1">
            Sign in with your FS BUILDER LITE Employee Code or Registered Email
          </p>
        </div>

        {/* API Health Status Banner */}
        {healthStatus === 'checking' && (
          <div className="bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-300 p-3 rounded-md text-xs font-semibold flex items-center gap-2">
            <Loader className="w-4 h-4 shrink-0 animate-spin text-blue-500" />
            <span>Connecting to API server… (attempt {retryCount + 1}/{MAX_RETRIES})</span>
          </div>
        )}
        {healthStatus === 'ok' && (
          <div className="bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-900 text-emerald-800 dark:text-emerald-300 p-3 rounded-md text-xs font-bold flex items-center gap-2">
            <CheckCircle className="w-4 h-4 shrink-0 text-emerald-600" />
            <span>API server is online — you may sign in.</span>
          </div>
        )}
        {healthStatus === 'failed' && (
          <div className="bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-300 p-3 rounded-md text-xs font-bold flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span>Backend unreachable after {MAX_RETRIES} attempts. Please start the backend and refresh the page.</span>
          </div>
        )}

        {/* Login error */}
        {error && (
          <div className="bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-300 p-3 rounded-md text-xs font-bold flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span>{error}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
              Employee Code / Email Address *
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                required
                placeholder="e.g. EMP001 or admin@swindia.in"
                value={loginId}
                onChange={(e) => setLoginId(e.target.value)}
                className="studio-input text-xs pl-9 py-2 w-full font-bold"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
              Password *
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="password"
                required
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="studio-input text-xs pl-9 py-2 w-full font-mono"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={buttonDisabled}
            className="w-full btn bg-orange-600 hover:bg-orange-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-bold py-2.5 rounded-md text-xs shadow-md transition-all flex items-center justify-center gap-2"
          >
            {loading ? 'Authenticating credentials...' : !apiReady ? 'Waiting for server…' : 'Sign In to Audit System'}
          </button>
        </form>

        {/* Quick Demo Logins */}
        <div className="border-t border-ca-border pt-4 space-y-2">
          <span className="text-[10px] font-bold text-ca-muted uppercase block text-center tracking-wider">
            Quick One-Click Demo Credentials:
          </span>
          <div className="grid grid-cols-2 gap-2 text-[10px]">
            <button type="button" disabled={buttonDisabled} onClick={() => handleQuickLogin('EMP001', 'Admin@123')}
              className="p-2 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded text-left hover:bg-rose-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
              <span className="font-bold text-rose-800 dark:text-rose-300 block">System Administrator</span>
              <span className="text-slate-500 font-mono">EMP001 (Admin@123)</span>
            </button>
            <button type="button" disabled={buttonDisabled} onClick={() => handleQuickLogin('EMP002', 'Partner@123')}
              className="p-2 bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-900 rounded text-left hover:bg-purple-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
              <span className="font-bold text-purple-800 dark:text-purple-300 block">Partner</span>
              <span className="text-slate-500 font-mono">EMP002 (Partner@123)</span>
            </button>
            <button type="button" disabled={buttonDisabled} onClick={() => handleQuickLogin('EMP003', 'Manager@123')}
              className="p-2 bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 rounded text-left hover:bg-blue-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
              <span className="font-bold text-blue-800 dark:text-blue-300 block">Manager</span>
              <span className="text-slate-500 font-mono">EMP003 (Manager@123)</span>
            </button>
            <button type="button" disabled={buttonDisabled} onClick={() => handleQuickLogin('EMP004', 'Exec@123')}
              className="p-2 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900 rounded text-left hover:bg-emerald-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
              <span className="font-bold text-emerald-800 dark:text-emerald-300 block">Executive</span>
              <span className="text-slate-500 font-mono">EMP004 (Exec@123)</span>
            </button>
          </div>
        </div>

        <div className="text-[10px] text-center text-slate-400 border-t border-ca-border pt-3">
          Session Timeout Policy: Strict 30 Minutes JWT Inactivity Expiry.
        </div>
      </div>
    </div>
  );
};
