import React, { useState } from 'react';
import { UserAccount, FactorySettings } from '../types/grn';
import { ShieldCheck, UserCheck, Lock, Building2, CheckCircle2 } from 'lucide-react';
import { PWAInstallBanner } from './PWAInstallBanner';

interface LoginScreenProps {
  users: UserAccount[];
  settings: FactorySettings;
  onLoginSuccess: (user: UserAccount, token: string) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ users, settings, onLoginSuccess }) => {
  const [selectedUser, setSelectedUser] = useState<UserAccount | null>(users[0] || null);
  const [pin, setPin] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const handleLogin = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!selectedUser) {
      setError('कृपया पहले अपना नाम चुनें');
      return;
    }
    if (!pin) {
      setError('कृपया अपना 4-अंकों का पिन दर्ज करें');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: selectedUser.id, pin: pin.trim() })
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || 'पिन सही नहीं है');
      }

      const data = await res.json();
      onLoginSuccess(data.user, data.token);
    } catch (err: any) {
      setError(err.message || 'लॉगिन विफल रहा');
    } finally {
      setIsLoading(false);
    }
  };

  // Quick fill pin for demo/easy gate operation
  const quickSelectUser = (u: UserAccount) => {
    setSelectedUser(u);
    setPin(u.pin);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center p-4">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl text-white">
        
        {/* Brand Header */}
        <div className="text-center mb-6">
          <div className="w-16 h-16 rounded-2xl bg-teal-600/20 border border-teal-500/40 mx-auto flex items-center justify-center text-teal-400 mb-3 shadow-inner">
            <Building2 className="w-9 h-9" />
          </div>
          <h1 className="text-xl sm:text-2xl font-black text-white tracking-wide">
            {settings.factoryName}
          </h1>
          <p className="text-xs sm:text-sm text-teal-300 font-medium mt-1">
            गेट माल प्राप्ति रसीद प्रणाली (GRN Portal)
          </p>
        </div>

        {/* User Selection */}
        <div className="mb-5">
          <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
            1. अपना नाम चुनें (Select User):
          </label>
          <div className="space-y-2">
            {users.map((u) => {
              const isSelected = selectedUser?.id === u.id;
              return (
                <button
                  type="button"
                  key={u.id}
                  onClick={() => quickSelectUser(u)}
                  className={`w-full p-3 rounded-2xl flex items-center justify-between text-left transition border-2 ${
                    isSelected
                      ? 'bg-teal-950/80 border-teal-500 text-white shadow-md'
                      : 'bg-slate-800/60 border-slate-700/60 text-slate-300 hover:border-slate-600'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-sm ${
                      isSelected ? 'bg-teal-500 text-slate-950' : 'bg-slate-700 text-slate-300'
                    }`}>
                      {u.name.charAt(0)}
                    </div>
                    <div>
                      <div className="font-bold text-sm sm:text-base">{u.name}</div>
                      <div className="text-xs text-slate-400">
                        {u.role === 'admin' ? '🏢 मालिक / एडमिन' : `📍 ${u.gateName}`}
                      </div>
                    </div>
                  </div>
                  {isSelected && <CheckCircle2 className="w-5 h-5 text-teal-400 shrink-0" />}
                </button>
              );
            })}
          </div>
        </div>

        {/* PIN Entry */}
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">
              2. 4-अंकों का पिन (PIN):
            </label>
            <div className="relative">
              <input
                type="password"
                inputMode="numeric"
                maxLength={6}
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                placeholder="पिन दर्ज करें..."
                className="w-full bg-slate-800 border-2 border-slate-700 focus:border-teal-400 rounded-2xl px-4 py-3.5 text-center text-2xl font-mono tracking-widest text-white outline-none transition"
              />
              <Lock className="w-5 h-5 text-slate-500 absolute left-4 top-1/2 -translate-y-1/2" />
            </div>
            {selectedUser && (
              <p className="text-[11px] text-teal-400/80 mt-1.5 text-center">
                सुझाव: {selectedUser.name} का पिन है: <span className="font-mono font-bold text-teal-300 underline">{selectedUser.pin}</span>
              </p>
            )}
          </div>

          {error && (
            <div className="p-3 bg-red-950/80 border border-red-500/60 rounded-xl text-red-200 text-xs font-semibold text-center">
              ⚠️ {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-4 bg-teal-600 hover:bg-teal-500 text-white font-extrabold text-base sm:text-lg rounded-2xl shadow-lg shadow-teal-900/40 transition active:scale-98 flex items-center justify-center gap-2 cursor-pointer"
          >
            {isLoading ? (
              <span>जांच हो रही है...</span>
            ) : (
              <>
                <UserCheck className="w-5 h-5" />
                <span>प्रवेश करें (Login)</span>
              </>
            )}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-slate-800/80 flex justify-center">
          <PWAInstallBanner />
        </div>

      </div>
    </div>
  );
};
