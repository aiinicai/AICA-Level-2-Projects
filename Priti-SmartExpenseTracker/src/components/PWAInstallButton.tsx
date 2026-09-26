import React, { useState } from 'react';
import {
  Download,
  Share2,
  X,
  Smartphone,
  Laptop,
  CheckCircle2,
  Sparkles,
  ArrowRight,
  ExternalLink,
} from 'lucide-react';
import { usePWAInstall } from '../hooks/usePWAInstall';

export const PWAInstallButton: React.FC = () => {
  const { isInstallable, isInstalled, isIOS, install } = usePWAInstall();
  const [showModal, setShowModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'mobile' | 'desktop'>('mobile');

  const handleClick = async () => {
    // If native prompt is ready (Chromium/Android), attempt direct prompt
    if (isInstallable) {
      const outcome = await install();
      if (!outcome) {
        setShowModal(true);
      }
    } else {
      // If prompt not available (e.g. inside iframe, Safari, or already installed), open guide
      setShowModal(true);
    }
  };

  return (
    <>
      {/* Prominent, Colorful, Always-Visible Install Button */}
      <button
        onClick={handleClick}
        className="group relative inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 via-teal-600 to-indigo-600 hover:from-emerald-500 hover:via-teal-500 hover:to-indigo-500 text-white px-3.5 py-1.5 text-xs font-bold shadow-md shadow-emerald-600/25 hover:shadow-lg hover:shadow-indigo-500/25 transition-all duration-200 active:scale-95 cursor-pointer border border-white/20"
        title="Install Smart Expense Tracker on your device"
      >
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-300 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-white"></span>
        </span>
        <Download className="w-3.5 h-3.5 transition-transform group-hover:-translate-y-0.5" />
        <span className="tracking-wide">
          {isInstalled ? 'App Installed' : 'Install App'}
        </span>
      </button>

      {/* Comprehensive, Colorful Installation Guide Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
            {/* Colorful Modal Header */}
            <div className="relative bg-gradient-to-r from-emerald-600 via-teal-600 to-indigo-600 p-5 text-white">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-md flex items-center justify-center shadow-inner">
                    <Download className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-base font-extrabold tracking-tight">
                      Install Smart Expense Tracker
                    </h3>
                    <p className="text-xs text-emerald-100 font-medium">
                      Fast, lightweight & works completely offline
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setShowModal(false)}
                  className="p-1.5 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Direct One-Click Install if prompt is ready */}
              {isInstallable && (
                <div className="mt-4 pt-3 border-t border-white/20">
                  <button
                    onClick={async () => {
                      const res = await install();
                      if (res) setShowModal(false);
                    }}
                    className="w-full py-2.5 px-4 rounded-xl bg-white hover:bg-emerald-50 text-emerald-800 font-bold text-xs shadow-md transition active:scale-98 flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <Sparkles className="w-4 h-4 text-emerald-600" />
                    <span>Click to Install Now (1-Tap)</span>
                  </button>
                </div>
              )}
            </div>

            {/* Platform Selector Tabs */}
            <div className="flex border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 p-1.5 gap-1.5">
              <button
                onClick={() => setActiveTab('mobile')}
                className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-bold rounded-xl transition cursor-pointer ${
                  activeTab === 'mobile'
                    ? 'bg-white dark:bg-slate-800 text-emerald-600 dark:text-emerald-400 shadow-xs'
                    : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                }`}
              >
                <Smartphone className="w-4 h-4" />
                <span>iPhone & Android</span>
              </button>
              <button
                onClick={() => setActiveTab('desktop')}
                className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-bold rounded-xl transition cursor-pointer ${
                  activeTab === 'desktop'
                    ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-xs'
                    : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                }`}
              >
                <Laptop className="w-4 h-4" />
                <span>Chrome / Edge Desktop</span>
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 space-y-4">
              {activeTab === 'mobile' ? (
                <div className="space-y-3.5 text-xs text-slate-600 dark:text-slate-300">
                  {/* iOS Safari Guide */}
                  <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-3.5 bg-slate-50/50 dark:bg-slate-800/30 space-y-2">
                    <span className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5 text-xs">
                      <span className="w-2 h-2 rounded-full bg-emerald-500" />
                      iPhone / iPad (Safari)
                    </span>
                    <ol className="list-decimal list-inside space-y-1.5 text-slate-600 dark:text-slate-300 pl-1">
                      <li>
                        Tap the <strong className="text-slate-900 dark:text-white font-semibold">Share</strong> button (<Share2 className="w-3.5 h-3.5 inline mx-0.5 text-sky-600" />) in Safari.
                      </li>
                      <li>
                        Scroll down and tap <strong className="text-slate-900 dark:text-white font-semibold">Add to Home Screen</strong>.
                      </li>
                      <li>
                        Tap <strong className="text-emerald-600 font-semibold">Add</strong> in the top-right corner.
                      </li>
                    </ol>
                  </div>

                  {/* Android Chrome Guide */}
                  <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-3.5 bg-slate-50/50 dark:bg-slate-800/30 space-y-2">
                    <span className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5 text-xs">
                      <span className="w-2 h-2 rounded-full bg-indigo-500" />
                      Android (Chrome / Samsung Internet)
                    </span>
                    <ol className="list-decimal list-inside space-y-1.5 text-slate-600 dark:text-slate-300 pl-1">
                      <li>
                        Tap the <strong className="text-slate-900 dark:text-white font-semibold">three dots (⋮)</strong> menu in top right.
                      </li>
                      <li>
                        Tap <strong className="text-slate-900 dark:text-white font-semibold">Install App</strong> or <strong className="text-slate-900 dark:text-white font-semibold">Add to Home screen</strong>.
                      </li>
                    </ol>
                  </div>
                </div>
              ) : (
                /* Desktop Instructions */
                <div className="space-y-3.5 text-xs text-slate-600 dark:text-slate-300">
                  <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-3.5 bg-slate-50/50 dark:bg-slate-800/30 space-y-2">
                    <span className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5 text-xs">
                      <span className="w-2 h-2 rounded-full bg-teal-500" />
                      Chrome or Edge on Windows / Mac
                    </span>
                    <ol className="list-decimal list-inside space-y-1.5 text-slate-600 dark:text-slate-300 pl-1">
                      <li>
                        Look at the right side of your browser URL bar for the <strong className="text-slate-900 dark:text-white font-semibold">Install icon (⊕ or ⬇)</strong>.
                      </li>
                      <li>
                        Click it and select <strong className="text-emerald-600 font-semibold">Install</strong> to run Smart Expense in its own fast, standalone window!
                      </li>
                      <li>
                        Or click the browser menu (⋮) → <strong className="text-slate-900 dark:text-white font-semibold">Save and share</strong> → <strong className="text-slate-900 dark:text-white font-semibold">Install Smart Expense</strong>.
                      </li>
                    </ol>
                  </div>
                </div>
              )}

              {/* Benefits Banner */}
              <div className="flex items-center gap-3 p-3 rounded-xl bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-950/40 dark:to-teal-950/40 border border-emerald-200 dark:border-emerald-800/50">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <p className="text-[11px] text-slate-700 dark:text-slate-300 font-medium">
                  Installed app launches instantly, stores all transactions locally on your device, and works with or without internet.
                </p>
              </div>

              {/* Close Button */}
              <button
                onClick={() => setShowModal(false)}
                className="w-full py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-white text-white dark:text-slate-900 font-bold text-xs transition cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
