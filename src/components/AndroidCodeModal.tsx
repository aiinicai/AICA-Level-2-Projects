import React, { useState } from 'react';
import {
  X,
  Smartphone,
  ShieldCheck,
  Lock,
  Cpu,
  Layers,
  CheckCircle2,
  Bell,
  Activity,
  AlertCircle,
  EyeOff,
  Zap,
  Building
} from 'lucide-react';
import { UAE_BANKS_LIST } from '../types/finance';

interface AndroidCodeModalProps {
  onClose: () => void;
}

export const AndroidCodeModal: React.FC<AndroidCodeModalProps> = ({ onClose }) => {
  const [activeTab, setActiveTab] = useState<'engine' | 'security' | 'banks' | 'setup'>('engine');

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end sm:justify-center items-center bg-black/85 backdrop-blur-sm p-0 sm:p-4 overflow-hidden animate-fade-in">
      <div className="w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[94vh] sm:max-h-[90vh]">
        {/* Header */}
        <div className="p-5 sm:p-6 bg-slate-950 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-2xl bg-teal-500/20 text-teal-400 border border-teal-500/30 flex items-center justify-center shrink-0">
              <Cpu className="w-6 h-6 text-teal-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base sm:text-lg font-bold text-white">
                  Android Background Service Engine
                </h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                  Active &amp; Protected
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Proprietary On-Device Bank Notification Interceptor • Native Android Service
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
            onClick={() => setActiveTab('engine')}
            className={`py-2 px-3.5 rounded-xl font-bold whitespace-nowrap transition cursor-pointer ${
              activeTab === 'engine'
                ? 'bg-teal-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white hover:bg-slate-900'
            }`}
          >
            ⚡ Service Architecture
          </button>
          <button
            onClick={() => setActiveTab('security')}
            className={`py-2 px-3.5 rounded-xl font-bold whitespace-nowrap transition cursor-pointer ${
              activeTab === 'security'
                ? 'bg-teal-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white hover:bg-slate-900'
            }`}
          >
            🛡️ Security &amp; IP Protection
          </button>
          <button
            onClick={() => setActiveTab('banks')}
            className={`py-2 px-3.5 rounded-xl font-bold whitespace-nowrap transition cursor-pointer ${
              activeTab === 'banks'
                ? 'bg-teal-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white hover:bg-slate-900'
            }`}
          >
            🏦 Supported UAE Banks ({UAE_BANKS_LIST.length})
          </button>
          <button
            onClick={() => setActiveTab('setup')}
            className={`py-2 px-3.5 rounded-xl font-bold whitespace-nowrap transition cursor-pointer ${
              activeTab === 'setup'
                ? 'bg-teal-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white hover:bg-slate-900'
            }`}
          >
            📱 Phone Setup &amp; Activation
          </button>
        </div>

        {/* Content Body */}
        <div className="p-5 sm:p-6 space-y-6 text-xs text-slate-300 overflow-y-auto">
          {/* TAB 1: Service Architecture */}
          {activeTab === 'engine' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-gradient-to-r from-teal-950/40 to-slate-900 border border-teal-500/30 flex items-start gap-3.5">
                <div className="w-10 h-10 rounded-xl bg-teal-500/20 text-teal-400 flex items-center justify-center shrink-0 mt-0.5">
                  <Activity className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white mb-1">
                    24/7 Silent Background Notification Pipeline
                  </h4>
                  <p className="text-slate-300 text-[11px] leading-relaxed">
                    The background engine hooks directly into Android's low-level system notification broadcast channel. It listens for verified banking alerts, extracts financial transaction details, converts international currencies to AED, and updates your ledger without needing any manual data entry.
                  </p>
                </div>
              </div>

              {/* Architecture Pillars */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
                  <div className="w-8 h-8 rounded-xl bg-teal-500/15 text-teal-400 flex items-center justify-center font-bold text-xs">
                    01
                  </div>
                  <h5 className="font-bold text-white text-xs">Notification Listener</h5>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Subscribes to system alerts with zero battery consumption. Filters incoming push messages from verified UAE banking apps and SMS messaging packages.
                  </p>
                </div>

                <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
                  <div className="w-8 h-8 rounded-xl bg-teal-500/15 text-teal-400 flex items-center justify-center font-bold text-xs">
                    02
                  </div>
                  <h5 className="font-bold text-white text-xs">Heuristic Parser Engine</h5>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Identifies amounts (AED/USD), card masks (•••• 1234), salary credits (WPS), merchant identities, and detects international foreign currency flags.
                  </p>
                </div>

                <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
                  <div className="w-8 h-8 rounded-xl bg-teal-500/15 text-teal-400 flex items-center justify-center font-bold text-xs">
                    03
                  </div>
                  <h5 className="font-bold text-white text-xs">On-Device Local Bridge</h5>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Dispatches the verified payload straight to your local ledger. No cloud proxies or external servers touch your banking alerts.
                  </p>
                </div>
              </div>

              {/* Status Checklist */}
              <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3">
                <h5 className="text-xs font-bold text-white uppercase tracking-wider text-teal-400">
                  Engine Diagnostic Status:
                </h5>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-[11px]">
                  <div className="flex items-center gap-2 p-2.5 rounded-xl bg-slate-900 border border-slate-850">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span className="text-slate-300">Background Service: <strong>Operational</strong></span>
                  </div>
                  <div className="flex items-center gap-2 p-2.5 rounded-xl bg-slate-900 border border-slate-850">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span className="text-slate-300">WPS Salary Auto-Crediting: <strong>Active</strong></span>
                  </div>
                  <div className="flex items-center gap-2 p-2.5 rounded-xl bg-slate-900 border border-slate-850">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span className="text-slate-300">Foreign Currency Peg (3.6725): <strong>Active</strong></span>
                  </div>
                  <div className="flex items-center gap-2 p-2.5 rounded-xl bg-slate-900 border border-slate-850">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span className="text-slate-300">Local Ledger Storage: <strong>Synced</strong></span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Security & IP Protection */}
          {activeTab === 'security' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-slate-950 border border-teal-500/30 flex items-start gap-3.5">
                <div className="w-10 h-10 rounded-xl bg-teal-500/20 text-teal-400 flex items-center justify-center shrink-0 mt-0.5">
                  <ShieldCheck className="w-5 h-5 text-teal-400" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white mb-1">
                    Intellectual Property &amp; Source Code Protection
                  </h4>
                  <p className="text-slate-300 text-[11px] leading-relaxed">
                    DirhamTrack's notification parser algorithms, Android listener implementation, and banking matching logic are compiled into hardened, obfuscated bytecode (ProGuard / R8).
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
                  <div className="flex items-center gap-2 text-white font-bold text-xs">
                    <EyeOff className="w-4 h-4 text-teal-400" />
                    <span>Protected Source Binaries</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Source code display and direct text copying are disabled to protect proprietary algorithms and application security integrity.
                  </p>
                </div>

                <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
                  <div className="flex items-center gap-2 text-white font-bold text-xs">
                    <Lock className="w-4 h-4 text-teal-400" />
                    <span>100% Local Device Privacy</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Bank alert texts never leave your mobile phone. No sensitive data, credit card numbers, or OTP tokens are transmitted to any cloud servers.
                  </p>
                </div>
              </div>

              <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-2 text-[11px]">
                <h5 className="font-bold text-white">Security Verification:</h5>
                <ul className="space-y-1.5 text-slate-400">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>Read-only notification scope (cannot send or delete SMS messages).</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>OTP &amp; sensitive 2FA security tokens are automatically ignored and discarded.</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>Full user control: deactivate notification access anytime in Android Settings.</span>
                  </li>
                </ul>
              </div>
            </div>
          )}

          {/* TAB 3: Supported UAE Banks */}
          {activeTab === 'banks' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    <Building className="w-4 h-4 text-teal-400" />
                    <span>Recognized Financial Institutions</span>
                  </h4>
                  <span className="text-[11px] text-teal-300 font-semibold bg-teal-500/15 px-2.5 py-0.5 rounded-full border border-teal-500/30">
                    {UAE_BANKS_LIST.length} Banks Covered
                  </span>
                </div>
                <p className="text-slate-400 text-[11px] mb-4">
                  DirhamTrack is equipped with heuristics to parse push notifications and SMS alerts from all major UAE banks and digital banking platforms:
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 text-[11px]">
                  {UAE_BANKS_LIST.map((bank, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded-xl bg-slate-900 border border-slate-850 flex items-center gap-2 text-slate-200"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 text-teal-400 shrink-0" />
                      <span className="truncate">{bank}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: Phone Setup & Activation */}
          {activeTab === 'setup' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-gradient-to-r from-teal-950/40 to-slate-900 border border-teal-500/30">
                <h4 className="text-sm font-bold text-white mb-1.5 flex items-center gap-2">
                  <Smartphone className="w-4 h-4 text-teal-400" />
                  <span>Activation Steps for Android Phone Devices</span>
                </h4>
                <p className="text-slate-300 text-[11px] leading-relaxed">
                  Follow these 3 quick steps on your Android Phone to allow the service to catch bank alerts:
                </p>
              </div>

              <div className="space-y-3">
                <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 flex items-start gap-3">
                  <div className="w-7 h-7 rounded-xl bg-teal-500/20 text-teal-400 font-bold flex items-center justify-center shrink-0 text-xs">
                    1
                  </div>
                  <div>
                    <h5 className="font-bold text-white text-xs mb-0.5">Grant Notification Access</h5>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      Open phone <strong>Settings</strong> &gt; search for <strong>Notification Access</strong> (or <strong>Device &amp; App Notifications</strong>). Locate <strong>DirhamTrack</strong> and toggle it <strong>ON</strong>.
                    </p>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 flex items-start gap-3">
                  <div className="w-7 h-7 rounded-xl bg-teal-500/20 text-teal-400 font-bold flex items-center justify-center shrink-0 text-xs">
                    2
                  </div>
                  <div>
                    <h5 className="font-bold text-white text-xs mb-0.5">Disable Battery Optimization (Android Settings)</h5>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      Go to <strong>Settings &gt; Apps &gt; DirhamTrack &gt; Battery</strong> and select <strong>Unrestricted</strong>. This prevents Android OS from pausing the background receiver when the screen is locked.
                    </p>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 flex items-start gap-3">
                  <div className="w-7 h-7 rounded-xl bg-teal-500/20 text-teal-400 font-bold flex items-center justify-center shrink-0 text-xs">
                    3
                  </div>
                  <div>
                    <h5 className="font-bold text-white text-xs mb-0.5">Ready to Auto-Record</h5>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      Make any transaction or receive your monthly salary alert. DirhamTrack will automatically capture the alert, calculate the amount in AED, and record it directly into your ledger!
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-3.5 sm:p-4 bg-slate-950 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Lock className="w-4 h-4 text-teal-400" />
            <span className="text-[11px]">Protected Native Engine • Developed by Fakhruddin</span>
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
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
