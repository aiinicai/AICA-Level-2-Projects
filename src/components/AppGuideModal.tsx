import React, { useState } from 'react';
import {
  X,
  BookOpen,
  Sparkles,
  Zap,
  ShieldAlert,
  Sliders,
  TrendingUp,
  CreditCard,
  Wallet,
  Smartphone,
  Lock,
  Calendar,
  Layers,
  CheckCircle2,
  AlertCircle,
  FileText,
  BadgeCheck,
  Heart
} from 'lucide-react';

interface AppGuideModalProps {
  onClose: () => void;
  onOpenAndroidGuide?: () => void;
}

export const AppGuideModal: React.FC<AppGuideModalProps> = ({ onClose, onOpenAndroidGuide }) => {
  const [activeTab, setActiveTab] = useState<'how_to_use' | 'banks' | 'faqs'>('how_to_use');

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end sm:justify-center items-center bg-black/85 backdrop-blur-sm p-0 sm:p-4 overflow-hidden animate-fade-in">
      <div className="w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[94vh] sm:max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-5 sm:p-6 bg-slate-950 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-2xl bg-teal-500/20 text-teal-400 border border-teal-500/30 flex items-center justify-center shrink-0">
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base sm:text-lg font-bold text-white">
                  DirhamTrack User Guide
                </h3>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-teal-500/15 text-teal-300 border border-teal-500/30">
                  v2.4
                </span>
              </div>
              <p className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
                <span>Smart UAE Personal Finance Companion</span>
                <span>•</span>
                <span className="text-teal-400 font-medium">Developed by Fakhruddin</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 p-2 bg-slate-950/80 border-b border-slate-800 text-xs overflow-x-auto shrink-0">
          <button
            onClick={() => setActiveTab('how_to_use')}
            className={`py-2 px-3.5 rounded-xl font-bold whitespace-nowrap transition cursor-pointer ${
              activeTab === 'how_to_use'
                ? 'bg-teal-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white hover:bg-slate-900'
            }`}
          >
            🚀 How to Use &amp; Workflow
          </button>
          <button
            onClick={() => setActiveTab('banks')}
            className={`py-2 px-3.5 rounded-xl font-bold whitespace-nowrap transition cursor-pointer ${
              activeTab === 'banks'
                ? 'bg-teal-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white hover:bg-slate-900'
            }`}
          >
            🏦 Supported Banks &amp; Red Flags
          </button>
          <button
            onClick={() => setActiveTab('faqs')}
            className={`py-2 px-3.5 rounded-xl font-bold whitespace-nowrap transition cursor-pointer ${
              activeTab === 'faqs'
                ? 'bg-teal-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white hover:bg-slate-900'
            }`}
          >
            💡 FAQs &amp; Privacy
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="p-5 sm:p-6 space-y-6 text-xs text-slate-300 overflow-y-auto">
          {/* TAB 1: HOW TO USE */}
          {activeTab === 'how_to_use' && (
            <div className="space-y-6">
              <div className="p-4 rounded-2xl bg-gradient-to-r from-teal-950/40 to-slate-900 border border-teal-500/30">
                <h4 className="text-sm font-bold text-white mb-1.5 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-teal-400" />
                  <span>Welcome to DirhamTrack!</span>
                </h4>
                <p className="text-slate-300 leading-relaxed text-[11px]">
                  DirhamTrack is purpose-built for UAE residents, expats, and professionals to effortlessly track multi-bank finances, capture notifications in real time, monitor salaries, convert international purchases, and keep track of monthly credit card limits in AED.
                </p>
              </div>

              <div>
                <h4 className="text-sm font-bold text-white mb-3">Quick Start in 3 Easy Steps:</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
                    <div className="w-7 h-7 rounded-lg bg-teal-500/20 text-teal-300 font-bold flex items-center justify-center text-xs">
                      1
                    </div>
                    <div className="font-bold text-white text-xs">Configure Accounts</div>
                    <p className="text-slate-400 text-[11px] leading-relaxed">
                      Go to the <strong>Accounts</strong> tab. Set up your Citi cards, Mashreq salary account, Emirates NBD, or Cash wallet with current balances and credit limits.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
                    <div className="w-7 h-7 rounded-lg bg-teal-500/20 text-teal-300 font-bold flex items-center justify-center text-xs">
                      2
                    </div>
                    <div className="font-bold text-white text-xs">Capture Transactions</div>
                    <p className="text-slate-400 text-[11px] leading-relaxed">
                      Use the <strong>Notification Interceptor</strong>. Real bank push notifications or SMS alerts from Citi, Mashreq, or Emirates NBD are automatically parsed and recorded into your ledger.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
                    <div className="w-7 h-7 rounded-lg bg-teal-500/20 text-teal-300 font-bold flex items-center justify-center text-xs">
                      3
                    </div>
                    <div className="font-bold text-white text-xs">Review &amp; Control</div>
                    <p className="text-slate-400 text-[11px] leading-relaxed">
                      Review foreign currencies under <strong>Red Flags</strong>, tweak conversion rates via the <strong>Alter</strong> button, verify genuine spends, and monitor category budgets.
                    </p>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider text-teal-400">
                  Daily Usage Workflow:
                </h4>
                <ul className="space-y-2 text-slate-300 text-[11px] leading-relaxed">
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <span><strong>Salary Day:</strong> Mashreq WPS salary alerts are auto-detected and automatically credited to your bank account balance.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <span><strong>Card Swipes:</strong> Citi and Emirates NBD grocery, dining, or fuel notifications deduct from your card balance with smart category tagging.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <span><strong>Online &amp; Travel Spends:</strong> USD transactions are auto-converted to AED at 3.6725 and flagged. Tap <strong>Alter</strong> to match your card statement rate or confirm genuine with 1 click.</span>
                  </li>
                </ul>
              </div>
            </div>
          )}


          {/* TAB 3: BANK INTEGRATIONS */}
          {activeTab === 'banks' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider text-teal-400">
                  Supported UAE Banks &amp; Providers:
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[11px]">
                  <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                    <div className="font-bold text-teal-300 mb-1">Citi Bank UAE</div>
                    <p className="text-slate-400">Card swipes, online transactions, international USD alerts, and credit limit tracking.</p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                    <div className="font-bold text-teal-300 mb-1">Mashreq Bank</div>
                    <p className="text-slate-400">WPS Salary transfers auto-credited to balance, debit card debits, Neo alerts, and international spend.</p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                    <div className="font-bold text-teal-300 mb-1">Emirates NBD &amp; Liv</div>
                    <p className="text-slate-400">ENBD credit/debit notifications, fuel, grocery, and dining transactions.</p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                    <div className="font-bold text-teal-300 mb-1">FAB &amp; Generic UAE SMS</div>
                    <p className="text-slate-400">First Abu Dhabi Bank alerts, CBD, RAKBANK, and standard banking SMS sender formats.</p>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
                <div className="font-bold text-white text-xs flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                  <span>How the Red Flag &amp; Alter System Works</span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed">
                  Whenever an international purchase (e.g. Amazon US, Steam, overseas hotel) is detected in USD, DirhamTrack converts it using the UAE Central Bank peg (1 USD = 3.6725 AED). To protect against unauthorized fraud or hidden bank conversion fees:
                </p>
                <ol className="list-decimal list-inside space-y-1 text-slate-400 text-[11px]">
                  <li>It is immediately marked with a <strong>Red Flag</strong> and highlighted in your dashboard.</li>
                  <li>Click <strong>Alter</strong> to adjust the exact AED charge, choose a bank markup preset (e.g., 3.7276 for 1.5% fee or 3.7827 for 3% fee), or update the currency.</li>
                  <li>Click <strong>Confirm Genuine</strong> once verified. It is verified and removed from Red Flags.</li>
                </ol>
              </div>
            </div>
          )}

          {/* TAB 4: FAQS */}
          {activeTab === 'faqs' && (
            <div className="space-y-4">
              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-1">
                <div className="font-bold text-white text-xs">Is my financial data secure?</div>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  Yes, 100%. DirhamTrack stores all accounts, budgets, and transactions locally on your device in encrypted local storage. No bank passwords or sensitive OTPs are ever transmitted to any third-party server.
                </p>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-1">
                <div className="font-bold text-white text-xs">How do I install DirhamTrack as an app?</div>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  DirhamTrack is a certified Progressive Web App (PWA). On Chrome (Android) or Safari (iPhone), tap <strong>"Add to Home Screen"</strong> or click the <strong>"Install App"</strong> button in the header for an offline, full-screen native mobile experience.
                </p>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-1">
                <div className="font-bold text-white text-xs">What is the default PIN?</div>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  The default security PIN is <code className="text-teal-300 bg-slate-900 px-1 py-0.5 rounded">1234</code>. You can lock the app anytime by clicking the lock icon in the top header.
                </p>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-1">
                <div className="font-bold text-white text-xs">How do I reset all data to start fresh?</div>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  Click the circular reset icon in the top header to clear all transactions and reset account balances with 1 click.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer with Developer Credit & Actions */}
        <div className="p-3.5 sm:p-4 bg-slate-950 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <BadgeCheck className="w-4 h-4 text-teal-400" />
            <span>
              Crafted with precision • <strong className="text-white">Developed by Fakhruddin</strong>
            </span>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              onClick={onClose}
              className="flex-1 sm:flex-none px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs rounded-xl border border-slate-700 transition cursor-pointer text-center"
            >
              Cancel
            </button>
            <button
              onClick={onClose}
              className="flex-1 sm:flex-none px-5 py-2 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-xl transition cursor-pointer shadow text-center"
            >
              Got It, Let's Track!
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
