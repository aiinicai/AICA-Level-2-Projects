import React from 'react';
import {
  Lock,
  FileText,
  Smartphone,
  ShieldCheck,
  RotateCcw,
  QrCode,
  BookOpen,
  TrendingUp
} from 'lucide-react';
import { PWAInstallButton } from './PWAInstallButton';

interface HeaderProps {
  activeTab: 'dashboard' | 'transactions' | 'budgets' | 'accounts' | 'subscriptions';
  onSelectTab: (tab: 'dashboard' | 'transactions' | 'budgets' | 'accounts' | 'subscriptions') => void;
  onOpenAddModal: () => void;
  onOpenReportModal: () => void;
  onOpenAndroidGuide: () => void;
  onOpenAppGuide: () => void;
  onOpenQrModal: () => void;
  onClearAllData: () => void;
  onLockApp: () => void;
  onOpenPinSettings: () => void;
  isPinEnabled: boolean;
  onOpenVoiceModal?: () => void;
  onOpenFraudModal?: () => void;
  onOpenForecastModal?: () => void;
  onOpenAssistantModal?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onSelectTab,
  onOpenAddModal,
  onOpenReportModal,
  onOpenAndroidGuide,
  onOpenAppGuide,
  onOpenQrModal,
  onClearAllData,
  onLockApp,
  onOpenPinSettings,
  isPinEnabled,
  onOpenVoiceModal,
  onOpenFraudModal,
  onOpenForecastModal,
  onOpenAssistantModal
}) => {
  return (
    <header
      className="sticky top-0 z-40 bg-slate-900/95 backdrop-blur-md border-b border-slate-800 transition-all"
      style={{ paddingTop: 'max(14px, env(safe-area-inset-top, 14px))' }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 sm:h-16 flex items-center justify-between gap-4 sm:gap-6">
        {/* Zone 1: Brand Wordmark with Developer Attribution */}
        <button
          onClick={() => onSelectTab('dashboard')}
          className="text-lg font-extrabold tracking-tight text-white hover:text-teal-400 transition whitespace-nowrap shrink-0 flex items-center gap-2.5 cursor-pointer"
        >
          <div className="w-8 h-8 rounded-lg bg-teal-500/20 text-teal-400 border border-teal-500/30 flex items-center justify-center font-black text-sm">
            د.إ
          </div>
          <div className="flex flex-col text-left">
            <span className="leading-tight">DirhamTrack</span>
            <span className="text-[10px] font-normal text-slate-400 block leading-tight">
              by <span className="text-teal-400 font-bold">Fakhruddin</span>
            </span>
          </div>
        </button>

        {/* Zone 2: 4-5 concise single-line nav links */}
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-300">
          <button
            onClick={() => onSelectTab('dashboard')}
            className={`whitespace-nowrap shrink-0 transition cursor-pointer ${
              activeTab === 'dashboard'
                ? 'text-teal-400 font-bold border-b-2 border-teal-400 pb-1'
                : 'hover:text-white'
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => onSelectTab('transactions')}
            className={`whitespace-nowrap shrink-0 transition cursor-pointer ${
              activeTab === 'transactions'
                ? 'text-teal-400 font-bold border-b-2 border-teal-400 pb-1'
                : 'hover:text-white'
            }`}
          >
            Transactions
          </button>
          <button
            onClick={() => onSelectTab('budgets')}
            className={`whitespace-nowrap shrink-0 transition cursor-pointer ${
              activeTab === 'budgets'
                ? 'text-teal-400 font-bold border-b-2 border-teal-400 pb-1'
                : 'hover:text-white'
            }`}
          >
            Budgets
          </button>
          <button
            onClick={() => onSelectTab('accounts')}
            className={`whitespace-nowrap shrink-0 transition cursor-pointer ${
              activeTab === 'accounts'
                ? 'text-teal-400 font-bold border-b-2 border-teal-400 pb-1'
                : 'hover:text-white'
            }`}
          >
            Accounts
          </button>
          <button
            onClick={() => onSelectTab('subscriptions')}
            className={`whitespace-nowrap shrink-0 transition cursor-pointer ${
              activeTab === 'subscriptions'
                ? 'text-teal-400 font-bold border-b-2 border-teal-400 pb-1'
                : 'hover:text-white'
            }`}
          >
            Recurring Bills
          </button>
        </nav>

        {/* Zone 3: Primary Action and Quick Utility Buttons */}
        <div className="flex items-center gap-2 shrink-0">
          {/* App Guide Button */}
          <button
            onClick={onOpenAppGuide}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-teal-500/15 text-teal-300 border border-teal-500/30 text-xs font-semibold hover:bg-teal-500/25 transition cursor-pointer"
            title="How to Use & Features Guide"
          >
            <BookOpen className="w-3.5 h-3.5 text-teal-400" />
            <span className="hidden sm:inline">App Guide</span>
          </button>

          {/* Android Guide Button */}
          <button
            onClick={onOpenAndroidGuide}
            className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 text-xs font-semibold transition cursor-pointer"
            title="Android Setup & Notification Interception Guide"
          >
            <Smartphone className="w-3.5 h-3.5 text-teal-400" />
            <span className="hidden sm:inline">Android</span>
          </button>

          {/* Scan Mobile QR Code */}
          <button
            onClick={onOpenQrModal}
            className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 text-xs font-semibold transition cursor-pointer"
            title="Scan QR Code to open on mobile"
          >
            <QrCode className="w-3.5 h-3.5 text-teal-400" />
            <span className="hidden sm:inline">Mobile QR</span>
          </button>

          {/* PWA Install Button */}
          <PWAInstallButton />

          {/* Statement Export */}
          <button
            onClick={onOpenReportModal}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition cursor-pointer"
            title="Monthly PDF/CSV Statement"
          >
            <FileText className="w-4 h-4" />
          </button>

          {/* Clear Data Reset */}
          <button
            onClick={onClearAllData}
            className="hidden sm:flex p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition cursor-pointer"
            title="Clear All Stored Data"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Lock App / Security PIN Trigger */}
          <div className="flex items-center gap-1">
            <button
              onClick={isPinEnabled ? onLockApp : onOpenPinSettings}
              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg border text-xs font-semibold transition cursor-pointer ${
                isPinEnabled
                  ? 'bg-teal-500/15 border-teal-500/30 text-teal-300 hover:bg-teal-500/25'
                  : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-white'
              }`}
              title={isPinEnabled ? 'Lock App Now with PIN' : 'Set up PIN Security'}
            >
              <Lock className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{isPinEnabled ? 'Lock' : 'Set PIN'}</span>
            </button>

            {isPinEnabled && (
              <button
                onClick={onOpenPinSettings}
                className="p-1.5 text-slate-400 hover:text-teal-300 hover:bg-slate-800 rounded-lg transition cursor-pointer text-[10px]"
                title="PIN Security Settings"
              >
                ⚙️
              </button>
            )}
          </div>
        </div>
      </div>

    </header>
  );
};
