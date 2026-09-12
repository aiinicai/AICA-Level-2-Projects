import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Tag, Lock, Mail, ArrowRight, ShieldCheck, UserCheck } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please enter both email and password.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid email or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const setDemoUser = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError('');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex flex-col justify-center items-center p-4">
      {/* Container */}
      <div className="max-w-md w-full">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex p-3 rounded-2xl bg-blue-600/20 border border-blue-500/30 text-blue-400 mb-4 shadow-xl">
            <Tag className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Asset Tagging Management System
          </h1>
          <p className="text-xs text-slate-400 mt-1 font-medium">
            Multi-Company Fixed Asset & Inventory Label Generation Engine
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-8 shadow-2xl backdrop-blur-md">
          <h2 className="text-lg font-bold text-white mb-6">Sign In to Workspace</h2>

          {error && (
            <div className="mb-5 bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg p-3 text-xs font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Work Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold rounded-lg py-2.5 text-xs shadow-lg shadow-blue-600/30 transition flex items-center justify-center gap-2"
            >
              <span>{loading ? 'Authenticating...' : 'Sign In'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Quick Demo Credentials */}
          <div className="mt-8 pt-6 border-t border-slate-800">
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-3">
              Initial Demo Credentials:
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setDemoUser('prasanth@gmail.com', '123456789')}
                className="flex items-center gap-2 p-2 rounded-lg bg-slate-950 border border-slate-800 hover:border-blue-500/50 text-left transition group"
              >
                <ShieldCheck className="w-4 h-4 text-blue-400 group-hover:text-blue-300 shrink-0" />
                <div className="truncate">
                  <div className="text-[11px] font-bold text-slate-200">Prasanth (Admin)</div>
                  <div className="text-[10px] text-slate-500">Full Access</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setDemoUser('mahesh@gmail.com', '987654321')}
                className="flex items-center gap-2 p-2 rounded-lg bg-slate-950 border border-slate-800 hover:border-emerald-500/50 text-left transition group"
              >
                <UserCheck className="w-4 h-4 text-emerald-400 group-hover:text-emerald-300 shrink-0" />
                <div className="truncate">
                  <div className="text-[11px] font-bold text-slate-200">Mahesh (User)</div>
                  <div className="text-[10px] text-slate-500">Standard Role</div>
                </div>
              </button>
            </div>
          </div>
        </div>

        <div className="text-center text-[11px] text-slate-500 mt-6">
          Enterprise Data Isolation • SHA-256 / Bcrypt Auth • SQLite WAL Storage
        </div>
      </div>
    </div>
  );
};
