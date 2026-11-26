import React from 'react';
import { CalendarCheck2, FileSpreadsheet, ShieldCheck, Users } from 'lucide-react';

interface SignInScreenProps {
  onSignIn: () => void;
  onDemo?: (role: 'admin' | 'manager' | 'employee') => void;
  signingIn: boolean;
  error: string | null;
}

export const SignInScreen: React.FC<SignInScreenProps> = ({ onSignIn, onDemo, signingIn, error }) => {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between p-6 md:p-10">
      <header className="max-w-6xl w-full mx-auto flex items-center justify-between gap-8 py-2">
        <span className="text-lg font-bold tracking-tight text-slate-900 font-display whitespace-nowrap shrink-0">
          TimeRecordingSystem
        </span>
        <span className="text-xs text-slate-500 whitespace-nowrap shrink-0">
          Employee Leave &amp; Balance Operations
        </span>
      </header>

      <main className="max-w-5xl w-full mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch my-8">
        <section className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-8 md:p-10 flex flex-col justify-between space-y-8">
          <div className="space-y-4">
            <p className="text-xs font-medium text-slate-500">
              Leave Balance Database · Dynamic Roster Sync · Manager Approvals
            </p>
            <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-slate-900 text-balance leading-tight">
              Leave accounting and team approvals synced to your company sheet.
            </h1>
            <p className="text-base text-slate-600 leading-relaxed max-w-xl">
              Sign in with your company Google account to view your Opening, Accrued, Availed, and Closing balances, apply for date-range leave, or review pending team approvals.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-200">
            <div className="space-y-1.5 pt-2">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <FileSpreadsheet className="w-4 h-4 text-slate-700" />
                <span>Google Sheet Roster Sync</span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Dynamically syncs designations, reporting managers, new joinees, and resignees.
              </p>
            </div>
            <div className="space-y-1.5 pt-2">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <Users className="w-4 h-4 text-slate-700" />
                <span>Instant Manager Pop-Up</span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Reporting managers see pending team leave requests immediately upon login.
              </p>
            </div>
            <div className="space-y-1.5 pt-2">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <CalendarCheck2 className="w-4 h-4 text-slate-700" />
                <span>Accurate Balance Math</span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Live Opening + Accrued − Availed = Closing calculation excluding holidays.
              </p>
            </div>
            <div className="space-y-1.5 pt-2">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <ShieldCheck className="w-4 h-4 text-slate-700" />
                <span>Role-Scoped Access</span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Verified Google identity routes approvals only to assigned reporting managers.
              </p>
            </div>
          </div>
        </section>

        <section className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-8 md:p-10 flex flex-col justify-center space-y-6">
          <div className="space-y-2">
            <h2 className="text-xl font-semibold text-slate-900">Sign in to your workspace</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Use your work Google email address listed in the company employee directory.
            </p>
          </div>

          {error && (
            <div className="p-3.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 leading-relaxed">
              {error}
            </div>
          )}

          <button
            type="button"
            onClick={onSignIn}
            disabled={signingIn}
            className="gsi-material-button w-full"
          >
            <div className="gsi-material-button-content-wrapper">
              <div className="gsi-material-button-icon">
                <svg
                  version="1.1"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 48 48"
                  style={{ display: 'block' }}
                >
                  <path
                    fill="#EA4335"
                    d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
                  />
                  <path
                    fill="#4285F4"
                    d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
                  />
                  <path
                    fill="#34A853"
                    d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
                  />
                  <path fill="none" d="M0 0h48v48H0z" />
                </svg>
              </div>
              <span className="gsi-material-button-contents">
                {signingIn ? 'Signing in...' : 'Sign in with Google'}
              </span>
            </div>
          </button>

          {onDemo && (
            <div className="border-t border-slate-200 pt-5 space-y-3">
              <div>
                <p className="text-sm font-semibold text-slate-900">Just exploring? Try the demo</p>
                <p className="text-xs text-slate-500 leading-relaxed mt-1">
                  No login or password needed. The demo uses made-up sample data that stays in your
                  browser; nothing is saved and no real employee data is shown.
                </p>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {([
                  ['admin', 'HR Admin'],
                  ['manager', 'Manager'],
                  ['employee', 'Employee'],
                ] as const).map(([role, label]) => (
                  <button
                    key={role}
                    type="button"
                    onClick={() => onDemo(role)}
                    className="px-3 py-2.5 text-xs font-semibold text-slate-800 bg-slate-100 border border-slate-200 rounded-lg hover:bg-slate-200 transition-colors cursor-pointer"
                  >
                    Demo as {label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <p className="text-xs text-slate-500 leading-relaxed">
            Your email identity is verified by Google Sign-In. HR administrators can also link a live Google Sheet to manage employee designations and reporting lines.
          </p>
        </section>
      </main>

      <footer className="max-w-6xl w-full mx-auto text-xs text-slate-500 py-2">
        TimeRecordingSystem · Timesheets and Leave
      </footer>
    </div>
  );
};
