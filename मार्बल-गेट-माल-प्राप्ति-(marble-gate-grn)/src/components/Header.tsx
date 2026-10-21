import React, { useState } from 'react';
import { UserAccount, FactorySettings } from '../types/grn';
import { PWAInstallBanner } from './PWAInstallBanner';
import { ShieldCheck, Wifi, WifiOff, RefreshCw, User, LogOut, Building2, AlertTriangle } from 'lucide-react';

interface HeaderProps {
  currentUser: UserAccount;
  settings: FactorySettings;
  isOnline: boolean;
  pendingSyncCount: number;
  isSyncing: boolean;
  onSyncNow: () => void;
  onLogout: () => void;
  activeTab: 'worker' | 'admin' | 'list';
  setActiveTab: (tab: 'worker' | 'admin' | 'list') => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentUser,
  settings,
  isOnline,
  pendingSyncCount,
  isSyncing,
  onSyncNow,
  onLogout,
  activeTab,
  setActiveTab,
}) => {
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  const handleLogoutClick = () => {
    if (pendingSyncCount > 0) {
      setShowLogoutConfirm(true);
    } else {
      onLogout();
    }
  };

  return (
    <header className="bg-slate-900 text-white shadow-lg sticky top-0 z-40 no-print">
      {/* Top Banner / Factory Name */}
      <div className="bg-teal-800 px-4 py-2 flex flex-wrap items-center justify-between gap-2 border-b border-teal-700/50">
        <div className="flex items-center gap-2">
          <Building2 className="w-5 h-5 text-amber-400 shrink-0" />
          <span className="font-bold text-sm sm:text-base tracking-wide text-white truncate max-w-[280px] sm:max-w-md">
            {settings.factoryName}
          </span>
        </div>

        {/* Sync & Network Status Badge */}
        <div className="flex items-center gap-2">
          {isOnline ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-600/60 shadow-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <Wifi className="w-3.5 h-3.5 text-emerald-400" />
              <span>सर्वर पर सुरक्षित (ऑनलाइन)</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-950/90 text-amber-300 border border-amber-600/60 shadow-xs">
              <WifiOff className="w-3.5 h-3.5 text-amber-400" />
              <span>ऑफलाइन (इस डिवाइस पर सुरक्षित)</span>
            </span>
          )}

          {/* Pending Sync Button */}
          {pendingSyncCount > 0 && (
            <button
              onClick={onSyncNow}
              disabled={isSyncing}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-md transition active:scale-95 animate-pulse"
              title="लंबित रसीदें सर्वर पर भेजें"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
              <span>{pendingSyncCount} सिंक बाकी (अभी सिंक करें)</span>
            </button>
          )}

          <PWAInstallBanner />
        </div>
      </div>

      {/* Main Nav Bar */}
      <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        {/* User Info & Gate */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal-700/60 border border-teal-500/30 flex items-center justify-center text-amber-300 font-black text-lg shadow-inner">
            {currentUser.name.charAt(0)}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base sm:text-lg text-white leading-tight">
                {currentUser.name}
              </span>
              <span className={`text-[11px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wider ${
                currentUser.role === 'admin' ? 'bg-purple-900/80 text-purple-200 border border-purple-600/50' : 'bg-slate-800 text-slate-300 border border-slate-700'
              }`}>
                {currentUser.role === 'admin' ? 'मालिक / एडमिन' : 'गेट ऑपरेटर'}
              </span>
            </div>
            <div className="text-xs text-slate-400 font-medium">
              📍 {currentUser.gateName}
            </div>
          </div>
        </div>

        {/* Tab Buttons & Logout */}
        <div className="flex items-center gap-2">
          {currentUser.role === 'admin' && (
            <div className="flex items-center bg-slate-800 p-1 rounded-xl border border-slate-700">
              <button
                onClick={() => setActiveTab('worker')}
                className={`px-3 py-1.5 rounded-lg text-xs sm:text-sm font-bold transition ${
                  activeTab === 'worker' ? 'bg-teal-600 text-white shadow-sm' : 'text-slate-300 hover:text-white'
                }`}
              >
                गेट एंट्री
              </button>
              <button
                onClick={() => setActiveTab('admin')}
                className={`px-3 py-1.5 rounded-lg text-xs sm:text-sm font-bold transition ${
                  activeTab === 'admin' ? 'bg-teal-600 text-white shadow-sm' : 'text-slate-300 hover:text-white'
                }`}
              >
                मालिक डैशबोर्ड
              </button>
            </div>
          )}

          <button
            onClick={handleLogoutClick}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs sm:text-sm font-semibold bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 transition active:scale-95"
            title="लॉगआउट / यूजर बदलें"
          >
            <LogOut className="w-4 h-4 text-slate-400" />
            <span className="hidden sm:inline">लॉगआउट</span>
          </button>
        </div>
      </div>

      {/* Warning Modal if Logging out with Pending Syncs */}
      {showLogoutConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl text-slate-900">
            <div className="flex items-center gap-3 text-amber-600 pb-3 border-b border-slate-100">
              <AlertTriangle className="w-8 h-8 shrink-0" />
              <h3 className="text-lg font-bold text-slate-900">चेतावनी: सिंक बाकी है!</h3>
            </div>
            
            <p className="mt-3 text-sm text-slate-700 leading-relaxed">
              इस डिवाइस पर <strong>{pendingSyncCount} माल प्राप्ति रसीदें</strong> अभी तक सर्वर पर सिंक नहीं हुई हैं। यदि आप इंटरनेट कनेक्ट किए बिना लॉगआउट करते हैं या ब्राउज़र कैश साफ करते हैं, तो डेटा खो सकता है।
            </p>

            <div className="mt-6 flex flex-col sm:flex-row gap-2">
              <button
                onClick={() => {
                  setShowLogoutConfirm(false);
                  onSyncNow();
                }}
                className="flex-1 py-3 px-4 bg-teal-700 hover:bg-teal-800 text-white font-bold rounded-xl text-sm transition"
              >
                पहले सिंक करें
              </button>
              <button
                onClick={() => {
                  setShowLogoutConfirm(false);
                  onLogout();
                }}
                className="py-3 px-4 bg-slate-100 hover:bg-red-50 text-red-600 font-bold rounded-xl text-sm transition border border-slate-300"
              >
                फिर भी लॉगआउट करें
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};
