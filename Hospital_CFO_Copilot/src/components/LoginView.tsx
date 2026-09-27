import React, { useState } from 'react';
import { AlertCircle, Shield, Lock, Info } from 'lucide-react';
import { signInWithGoogle } from '../services/authService';
import { UserSession } from '../types';

interface LoginViewProps {
  onLoginSuccess: (session: UserSession) => void;
}

export const LoginView: React.FC<LoginViewProps> = ({ onLoginSuccess }) => {
  const [error, setError] = useState<string | null>(null);
  const [isPopupBlocked, setIsPopupBlocked] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleGoogleLogin = async () => {
    setError(null);
    setIsPopupBlocked(false);
    setIsLoading(true);
    try {
      const res = await signInWithGoogle();
      if (res.success && res.session) {
        onLoginSuccess(res.session);
      } else {
        if (res.popupBlocked) {
          setIsPopupBlocked(true);
        }
        setError(
          res.error ||
            'Access not authorised. Please verify that your Google account is registered in the hospital directory.'
        );
      }
    } catch {
      setError('Sign-in could not be completed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-between py-10 px-4 sm:px-6 lg:px-8 relative overflow-hidden select-none">
      {/* Background Subtle Ambience */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-15%,rgba(13,148,136,0.12),transparent_70%)] pointer-events-none" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_right,rgba(15,23,42,0.8),transparent_50%)] pointer-events-none" />

      {/* Top spacer */}
      <div className="hidden sm:block" />

      {/* Centered Authentication Card */}
      <div className="w-full max-w-md mx-auto relative z-10 my-auto">
        <div className="bg-white rounded-2xl shadow-2xl border border-slate-200/80 p-7 sm:p-9">
          {/* Brand Header */}
          <div className="text-center mb-7">
            <div className="inline-flex h-13 w-13 items-center justify-center rounded-2xl bg-teal-50 border border-teal-200/80 text-teal-600 shadow-xs mb-3.5">
              <Shield className="h-6.5 w-6.5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Hospital CFO Copilot
            </h1>
            <p className="mt-1 text-xs font-medium text-slate-500">
              Financial Control &amp; Revenue Intelligence Portal
            </p>
          </div>

          {/* Popup Blocked Guidance */}
          {isPopupBlocked && (
            <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-900">
              <AlertCircle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
              <div className="leading-relaxed">
                <span className="font-semibold block mb-0.5 text-amber-950">Popup Window Blocked</span>
                Your browser blocked the sign-in window. Please allow popups for this site and try again.
              </div>
            </div>
          )}

          {/* Error / Notice Banner */}
          {error && !isPopupBlocked && (
            <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50/90 p-3.5 text-xs text-rose-800 leading-relaxed shadow-2xs">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-600 mt-0.5" />
              <div>
                <span className="font-bold block text-rose-900 mb-0.5">Notice</span>
                <span>{error}</span>
              </div>
            </div>
          )}

          {/* Google Sign-In Button */}
          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 hover:border-slate-400 text-slate-700 font-semibold text-sm shadow-sm transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed group focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2"
          >
            {isLoading ? (
              <div className="h-4 w-4 border-2 border-slate-300 border-t-teal-600 rounded-full animate-spin" />
            ) : (
              <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
            )}
            <span>{isLoading ? 'Verifying Authorization\u2026' : 'Continue with Google'}</span>
          </button>

          {/* Institutional Access Information */}
          <div className="mt-5 rounded-xl border border-slate-100 bg-slate-50/70 p-3 text-[11px] text-slate-500 space-y-1.5">
            <div className="flex items-center gap-1 text-slate-700 font-semibold text-[10px] uppercase tracking-wider">
              <Lock className="h-3 w-3 text-teal-600" />
              <span>Role-Based Access Controlled</span>
            </div>
            <p className="leading-relaxed">
              Access requires an authorised hospital user account provisioned by your system administrator.
              Your role and department are loaded from the hospital user directory after sign-in.
            </p>
            <div className="flex items-start gap-1 pt-0.5">
              <Info className="h-3 w-3 text-slate-400 mt-0.5 shrink-0" />
              <p className="leading-relaxed text-slate-400">
                Unauthorized Google accounts are denied access. This application does not grant self-service registration.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="w-full max-w-md mx-auto relative z-10 text-center text-xs text-slate-400 py-3 flex items-center justify-center gap-3">
        <span>Authorised Hospital Personnel Only</span>
        <span className="text-slate-600">&bull;</span>
        <span className="hover:text-slate-300 transition-colors">Audit Logged Session</span>
      </footer>
    </div>
  );
};
