import React from 'react';
import {
  Calendar,
  ShieldCheck,
  Plus,
  AlertCircle,
  Zap,
  Lock,
  User as UserIcon,
  LogOut,
  Eye,
  RefreshCw,
} from 'lucide-react';
import { formatDateDisplay, getTodayKolkata } from '../../utils/formatters';

interface HeaderProps {
  valuationDate: string;
  onValuationDateChange: (date: string) => void;
  onOpenAddModal: () => void;
  onOpenDiagnostics: () => void;
  onOpenIbjaFetch?: () => void;
  onOpenAuthModal?: () => void;
  onSignOut?: () => void;
  currentUser?: { email?: string; user_metadata?: { full_name?: string; avatar_url?: string } } | null;
  isSuperUser?: boolean;
  hasGapWarning?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  valuationDate,
  onValuationDateChange,
  onOpenAddModal,
  onOpenDiagnostics,
  onOpenIbjaFetch,
  onOpenAuthModal,
  onSignOut,
  currentUser,
  isSuperUser = false,
  hasGapWarning = false,
}) => {
  const latestDatasetDate = '2026-10-30';
  const todayKolkata = getTodayKolkata();

  const handleQuickDate = (type: 'today' | 'latest' | '1m' | '1y') => {
    if (type === 'today') {
      onValuationDateChange(todayKolkata);
    } else if (type === 'latest') {
      onValuationDateChange(latestDatasetDate);
    } else {
      const base = new Date(valuationDate);
      if (type === '1m') {
        base.setMonth(base.getMonth() - 1);
      } else if (type === '1y') {
        base.setFullYear(base.getFullYear() - 1);
      }
      const yyyy = base.getFullYear();
      const mm = String(base.getMonth() + 1).padStart(2, '0');
      const dd = String(base.getDate()).padStart(2, '0');
      onValuationDateChange(`${yyyy}-${mm}-${dd}`);
    }
  };

  const handleRecordClick = () => {
    if (!isSuperUser && onOpenAuthModal) {
      onOpenAuthModal();
    } else {
      onOpenAddModal();
    }
  };

  const handleQuickPurgeCache = async () => {
    try {
      if ('caches' in window) {
        const keys = await caches.keys();
        for (const k of keys) await caches.delete(k);
      }
      if ('serviceWorker' in navigator) {
        const regs = await navigator.serviceWorker.getRegistrations();
        for (const r of regs) await r.unregister();
      }
    } catch {
      // ignore
    }
    window.location.reload();
  };

  return (
    <header className="bg-white border-b border-[#E7E2DA] sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between py-3 gap-3">
          {/* Logo & Brand */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-md bg-[#FAF7F2] border border-[#D4AF37]/40 flex items-center justify-center text-[#B88B2A] shadow-xs">
                <svg
                  className="w-5 h-5 fill-current"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path d="M4 17h16l-2 4H6l-2-4zm1-3l3-7h8l3 7H5zm4.5-5l1.5-3.5h2L14.5 9h-5z" />
                </svg>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-lg font-bold tracking-tight text-[#1C1A18] leading-none">
                    Bullion Ledger
                  </h1>
                  <span className="text-[10px] uppercase font-semibold tracking-wider px-1.5 py-0.5 rounded bg-[#FBF6E9] text-[#B88B2A] border border-[#D4AF37]/30">
                    Production PWA
                  </span>
                </div>
                <p className="text-xs text-[#57534E] mt-0.5">
                  Physical Gold & Silver Portfolio Tracker
                </p>
              </div>
            </div>

            {/* Mobile quick actions */}
            <div className="flex items-center gap-2 md:hidden">
              {isSuperUser ? (
                <button
                  type="button"
                  onClick={onSignOut}
                  className="p-1.5 text-stone-500 hover:text-stone-800 text-xs border border-stone-200 rounded-lg flex items-center gap-1"
                  title="Sign Out"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={onOpenAuthModal}
                  className="px-2 py-1 text-[#B88B2A] bg-[#FBF6E9] border border-[#D4AF37]/40 rounded-lg text-xs font-semibold flex items-center gap-1"
                  title="Super User Login"
                >
                  <Lock className="w-3.5 h-3.5" />
                  <span>Login</span>
                </button>
              )}

              {onOpenIbjaFetch && (
                <button
                  type="button"
                  onClick={onOpenIbjaFetch}
                  className="p-2 text-[#B88B2A] bg-[#FBF6E9] border border-[#D4AF37]/40 rounded-lg text-xs flex items-center"
                  title="Source Today's IBJA Rates"
                >
                  <Zap className="w-4 h-4" />
                </button>
              )}
              <button
                type="button"
                onClick={onOpenDiagnostics}
                className="p-2 text-stone-600 hover:text-stone-900 bg-stone-50 border border-stone-200 rounded-lg text-xs flex items-center gap-1"
                title="System Diagnostics & Calculations Verification"
              >
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
              </button>
              <button
                type="button"
                onClick={handleQuickPurgeCache}
                className="p-2 text-stone-500 hover:text-stone-800 bg-stone-50 border border-stone-200 rounded-lg text-xs flex items-center"
                title="Purge cache & reload"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={handleRecordClick}
                className="px-3 py-1.5 bg-[#B88B2A] hover:bg-[#8E6B1D] text-white font-medium text-xs rounded-lg flex items-center gap-1 shadow-xs transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add</span>
              </button>
            </div>
          </div>

          {/* Shared Valuation Date Selector & Quick Toggles */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 bg-[#FAF7F2] p-2 rounded-lg border border-[#E7E2DA]">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-[#B88B2A] shrink-0" />
              <label
                htmlFor="valuation-date-input"
                className="text-xs font-semibold text-[#1C1A18] whitespace-nowrap"
              >
                Valuation as of:
              </label>
              <input
                id="valuation-date-input"
                type="date"
                value={valuationDate}
                onChange={(e) => e.target.value && onValuationDateChange(e.target.value)}
                className="bg-white border border-[#D6CEC5] rounded px-2 py-1 text-xs font-medium text-[#1C1A18] focus:outline-none focus:ring-1 focus:ring-[#B88B2A]"
              />
            </div>

            <div className="flex items-center gap-1 flex-wrap">
              <button
                type="button"
                onClick={() => handleQuickDate('latest')}
                className={`px-2 py-0.5 text-[11px] rounded font-medium transition-colors ${
                  valuationDate === latestDatasetDate
                    ? 'bg-[#B88B2A] text-white'
                    : 'bg-white hover:bg-stone-100 text-[#57534E] border border-stone-200'
                }`}
                title="Use latest historical closing rate (30-Oct-2026)"
              >
                30-Oct-2026
              </button>
              <button
                type="button"
                onClick={() => handleQuickDate('today')}
                className={`px-2 py-0.5 text-[11px] rounded font-medium transition-colors ${
                  valuationDate === todayKolkata
                    ? 'bg-[#B88B2A] text-white'
                    : 'bg-white hover:bg-stone-100 text-[#57534E] border border-stone-200'
                }`}
                title="Current Asia/Kolkata date"
              >
                Today
              </button>
              <button
                type="button"
                onClick={() => handleQuickDate('1m')}
                className="px-2 py-0.5 text-[11px] rounded font-medium bg-white hover:bg-stone-100 text-[#57534E] border border-stone-200"
              >
                -1M
              </button>
              <button
                type="button"
                onClick={() => handleQuickDate('1y')}
                className="px-2 py-0.5 text-[11px] rounded font-medium bg-white hover:bg-stone-100 text-[#57534E] border border-stone-200"
              >
                -1Y
              </button>
            </div>

            {hasGapWarning && (
              <span
                className="inline-flex items-center gap-1 text-[11px] text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200"
                title="Rate carried forward from preceding trading day or non-publication gap"
              >
                <AlertCircle className="w-3 h-3 text-amber-600" />
                Carried-forward
              </span>
            )}
          </div>

          {/* Desktop Right Actions */}
          <div className="hidden md:flex items-center gap-2.5">
            {/* Super User Status Badge / Auth Button */}
            {currentUser ? (
              isSuperUser ? (
                <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-amber-50 border border-[#D4AF37]/50 text-xs">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="font-bold text-[#B88B2A]">Super User</span>
                  <span className="text-[11px] text-stone-600 font-mono max-w-[140px] truncate" title={currentUser.email}>
                    ({currentUser.email})
                  </span>
                  <button
                    type="button"
                    onClick={onSignOut}
                    className="text-stone-400 hover:text-stone-700 p-0.5 ml-1 transition-colors"
                    title="Sign Out"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800">
                  <span className="font-bold text-rose-700">Restricted</span>
                  <span className="text-[10px] text-rose-600 truncate max-w-[100px]" title={currentUser.email}>
                    ({currentUser.email})
                  </span>
                  <button
                    type="button"
                    onClick={onSignOut}
                    className="text-rose-500 hover:text-rose-800 text-[10px] underline ml-1"
                    title="Sign Out and switch to kosamgo@gmail.com"
                  >
                    Logout
                  </button>
                </div>
              )
            ) : (
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-semibold px-2 py-1 rounded bg-stone-100 text-stone-600 border border-stone-200 flex items-center gap-1">
                  <Eye className="w-3 h-3 text-stone-500" />
                  <span>Public View</span>
                </span>
                <button
                  type="button"
                  onClick={onOpenAuthModal}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold text-stone-700 bg-white hover:bg-stone-50 border border-stone-300 rounded-lg shadow-2xs transition-colors"
                  title="Sign in as Super User (kosamgo@gmail.com) to record transactions"
                >
                  <Lock className="w-3.5 h-3.5 text-[#B88B2A]" />
                  <span>Super User Login</span>
                </button>
              </div>
            )}

            {onOpenIbjaFetch && (
              <button
                type="button"
                onClick={onOpenIbjaFetch}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-[#B88B2A] bg-[#FBF6E9] hover:bg-[#F5EDD5] border border-[#D4AF37]/40 rounded-lg shadow-2xs transition-colors"
                title="Source Today's IBJA Official PM Closing Rates"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>IBJA Rates</span>
              </button>
            )}

            <button
              type="button"
              onClick={onOpenDiagnostics}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-stone-700 bg-stone-50 hover:bg-stone-100 border border-stone-200 rounded-lg transition-colors shadow-2xs cursor-pointer"
            >
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Verify (11 Tests)</span>
            </button>

            <button
              type="button"
              onClick={handleQuickPurgeCache}
              className="p-1.5 text-stone-500 hover:text-stone-800 hover:bg-stone-100 border border-stone-200 rounded-lg transition-colors shadow-2xs cursor-pointer"
              title="Purge browser cache & force reload latest application build"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>

            <button
              type="button"
              onClick={handleRecordClick}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-[#B88B2A] hover:bg-[#8E6B1D] rounded-lg shadow-2xs transition-colors"
              title={isSuperUser ? 'Record a new purchase lot' : 'Requires Super User login'}
            >
              <Plus className="w-4 h-4" />
              <span>Record Purchase</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
