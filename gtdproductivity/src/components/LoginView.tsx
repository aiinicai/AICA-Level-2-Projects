import React, { useState } from 'react';
import {
  Award,
  ShieldCheck,
  User,
  KeyRound,
  CheckCircle2,
  ArrowRight,
  Sparkles,
  Lock,
  Building2,
  ChevronLeft,
  UserCheck
} from 'lucide-react';
import { UserSession, UserRole } from '../types/auth';

interface LoginViewProps {
  currentUser: UserSession;
  onLogin: (session: UserSession) => void;
  onBackToLanding: () => void;
  onGoToJuryCheck: () => void;
  onEnterWorkspace: () => void;
}

export const LoginView: React.FC<LoginViewProps> = ({
  currentUser,
  onLogin,
  onBackToLanding,
  onGoToJuryCheck,
  onEnterWorkspace,
}) => {
  const [activeTab, setActiveTab] = useState<'quick' | 'form'>('quick');
  const [membershipInput, setMembershipInput] = useState('177366');
  const [passwordInput, setPasswordInput] = useState('••••••••••');
  const [roleSelection, setRoleSelection] = useState<UserRole>('jury');
  const [loginSuccessNotice, setLoginSuccessNotice] = useState<string | null>(null);

  const handleQuickJuryLogin = () => {
    const session: UserSession = {
      role: 'jury',
      name: 'Honorable Jury Member',
      membershipNo: 'JURY-EVAL-2026',
      email: 'jury.evaluator@icai.org',
      title: 'ICAI Capstone Assessor & Evaluator',
      avatarInitials: 'JM',
      authenticated: true,
      loginTime: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    onLogin(session);
    setLoginSuccessNotice('Signed in as Honorable Jury Evaluator. Assessment Rubric is unlocked.');
    setTimeout(() => {
      onGoToJuryCheck();
    }, 800);
  };

  const handleQuickCandidateLogin = () => {
    const session: UserSession = {
      role: 'candidate',
      name: 'CA Prashant Nathvani',
      membershipNo: '177366',
      email: 'ca.prashant.nathvani@icai.org',
      title: 'Chartered Accountant & Project Author',
      avatarInitials: 'PN',
      authenticated: true,
      loginTime: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    onLogin(session);
    setLoginSuccessNotice('Signed in as CA Prashant Nathvani (M.No. 177366). Full author access enabled.');
    setTimeout(() => {
      onEnterWorkspace();
    }, 800);
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (roleSelection === 'candidate') {
      handleQuickCandidateLogin();
    } else {
      handleQuickJuryLogin();
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="mb-6">
        <button
          onClick={onBackToLanding}
          className="text-xs font-semibold text-slate-500 hover:text-slate-800 flex items-center gap-1.5 cursor-pointer transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>Back to Landing Page</span>
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
        {/* Top Header Card */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white p-6 sm:p-8">
          <div className="flex items-center justify-between gap-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-full text-xs font-semibold">
              <Award className="w-3.5 h-3.5 text-amber-400" />
              <span>ICAI Capstone Assessment Portal</span>
            </div>
            <div className="flex items-center gap-1 text-[11px] text-emerald-400 font-mono bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>TLS 1.3 Verified Sandbox</span>
            </div>
          </div>

          <h2 className="text-xl sm:text-2xl font-extrabold text-white mt-3">
            GTD Productivity Management System
          </h2>
          <p className="text-xs sm:text-sm text-slate-300 mt-1">
            Candidate: <strong className="text-white">CA Prashant Nathvani</strong> · ICAI Membership No: <span className="font-mono text-amber-300 font-bold">177366</span>
          </p>
        </div>

        {/* Success Toast / Notification */}
        {loginSuccessNotice && (
          <div className="mx-6 mt-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs sm:text-sm flex items-center gap-3 animate-fade-in">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <div>
              <p className="font-bold">{loginSuccessNotice}</p>
              <p className="text-emerald-700 text-xs mt-0.5">Redirecting to designated view...</p>
            </div>
          </div>
        )}

        <div className="p-6 sm:p-8 space-y-6">
          {/* Tab Selection */}
          <div className="flex border-b border-slate-200">
            <button
              onClick={() => setActiveTab('quick')}
              className={`pb-3 px-4 text-xs sm:text-sm font-bold border-b-2 transition-all cursor-pointer ${
                activeTab === 'quick'
                  ? 'border-teal-600 text-teal-800'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              ⚡ Fast Assessor & Author Access
            </button>
            <button
              onClick={() => setActiveTab('form')}
              className={`pb-3 px-4 text-xs sm:text-sm font-bold border-b-2 transition-all cursor-pointer ${
                activeTab === 'form'
                  ? 'border-teal-600 text-teal-800'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              🔒 Standard Credential Login
            </button>
          </div>

          {activeTab === 'quick' ? (
            /* Quick Access Mode for Jury & Candidate */
            <div className="space-y-4">
              <p className="text-xs text-slate-600">
                Choose a role below for instantaneous authenticated session initiation with pre-populated credentials:
              </p>

              {/* Option 1: Jury Assessor Login */}
              <div className="p-5 rounded-xl border-2 border-amber-300/80 bg-amber-50/50 hover:bg-amber-50 hover:border-amber-400 transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-amber-500 text-white flex items-center justify-center font-bold text-xs shadow-xs">
                      JM
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-900 text-sm">Honorable Jury Evaluator</h4>
                      <div className="text-[11px] text-amber-800 font-medium">ICAI Assessment Committee Panelist</div>
                    </div>
                  </div>
                  <p className="text-xs text-slate-600 pt-1">
                    Full grading authority, live rubric scoring, feature test verification, and candidate evaluation notes.
                  </p>
                </div>
                <button
                  onClick={handleQuickJuryLogin}
                  className="px-4 py-2.5 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded-lg text-xs transition-all shadow-xs flex items-center gap-1.5 shrink-0 cursor-pointer w-full sm:w-auto justify-center"
                >
                  <Award className="w-3.5 h-3.5" />
                  <span>Enter as Jury Assessor</span>
                </button>
              </div>

              {/* Option 2: Candidate Author Login */}
              <div className="p-5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-white hover:border-teal-300 transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center font-bold text-xs shadow-xs">
                      PN
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-900 text-sm">CA Prashant Nathvani</h4>
                      <div className="text-[11px] text-teal-700 font-mono font-medium">ICAI Membership No: 177366</div>
                    </div>
                  </div>
                  <p className="text-xs text-slate-600 pt-1">
                    Project Author session with sample dataset reset, live capture, context modification, and architecture inspection.
                  </p>
                </div>
                <button
                  onClick={handleQuickCandidateLogin}
                  className="px-4 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-lg text-xs transition-all shadow-xs flex items-center gap-1.5 shrink-0 cursor-pointer w-full sm:w-auto justify-center"
                >
                  <UserCheck className="w-3.5 h-3.5 text-teal-400" />
                  <span>Enter as Author</span>
                </button>
              </div>
            </div>
          ) : (
            /* Standard Login Form */
            <form onSubmit={handleFormSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Select Portal Role
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setRoleSelection('jury');
                      setMembershipInput('JURY-EVAL-2026');
                    }}
                    className={`p-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-2 cursor-pointer transition-all ${
                      roleSelection === 'jury'
                        ? 'border-amber-500 bg-amber-50 text-amber-900 shadow-2xs'
                        : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <Award className="w-4 h-4 text-amber-600" />
                    <span>Jury Assessor</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setRoleSelection('candidate');
                      setMembershipInput('177366');
                    }}
                    className={`p-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-2 cursor-pointer transition-all ${
                      roleSelection === 'candidate'
                        ? 'border-teal-500 bg-teal-50 text-teal-900 shadow-2xs'
                        : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <User className="w-4 h-4 text-teal-600" />
                    <span>Candidate (CA Prashant)</span>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  ICAI Membership / Assessor ID
                </label>
                <div className="relative">
                  <Building2 className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="text"
                    value={membershipInput}
                    onChange={(e) => setMembershipInput(e.target.value)}
                    className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-slate-300 text-xs font-mono focus:outline-hidden focus:ring-2 focus:ring-teal-500"
                    placeholder="e.g. 177366"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Secure Passkey / Token
                </label>
                <div className="relative">
                  <KeyRound className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="password"
                    value={passwordInput}
                    onChange={(e) => setPasswordInput(e.target.value)}
                    className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-slate-300 text-xs font-mono focus:outline-hidden focus:ring-2 focus:ring-teal-500"
                    placeholder="Enter passkey"
                    required
                  />
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" defaultChecked className="rounded text-teal-600" />
                  <span>Remember session in browser</span>
                </label>
                <span className="text-teal-700 hover:underline cursor-pointer">Demo Sandbox Mode</span>
              </div>

              <button
                type="submit"
                className="w-full py-3 bg-gradient-to-r from-teal-600 to-teal-700 hover:from-teal-700 hover:to-teal-800 text-white font-bold rounded-xl text-xs sm:text-sm transition-all shadow-md shadow-teal-600/20 cursor-pointer flex items-center justify-center gap-2 mt-4"
              >
                <Lock className="w-4 h-4" />
                <span>Authenticate & Access Environment</span>
              </button>
            </form>
          )}

          {/* Quick info note */}
          <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
            <span>Capstone Verification · Candidate: CA Prashant Nathvani (177366)</span>
            <button
              onClick={onEnterWorkspace}
              className="text-teal-700 hover:underline font-semibold cursor-pointer"
            >
              Skip directly to workspace →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
