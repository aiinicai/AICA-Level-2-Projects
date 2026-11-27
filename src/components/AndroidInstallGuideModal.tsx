import React, { useState } from 'react';
import {
  X,
  Smartphone,
  Bell,
  ShieldCheck,
  CheckCircle2,
  Download,
  Terminal,
  Cpu,
  Layers,
  ArrowRight,
  ExternalLink,
  Info
} from 'lucide-react';
import { usePWAInstall } from '../hooks/usePWAInstall';

interface AndroidInstallGuideModalProps {
  onClose: () => void;
  onOpenCodeViewer: () => void;
}

export const AndroidInstallGuideModal: React.FC<AndroidInstallGuideModalProps> = ({
  onClose,
  onOpenCodeViewer
}) => {
  const [activeTab, setActiveTab] = useState<'how_it_works' | 'pwa_install' | 'native_apk' | 'permission'>('how_it_works');
  const { isInstallable, install } = usePWAInstall();

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end sm:justify-center items-center bg-black/85 backdrop-blur-sm p-0 sm:p-4 overflow-hidden animate-fade-in">
      <div className="w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-3xl shadow-2xl flex flex-col max-h-[94vh] sm:max-h-[90vh] overflow-hidden">
        {/* Modal Header - Fixed & sticky */}
        <div className="p-4 sm:p-5 bg-slate-950 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-teal-500/20 text-teal-400 border border-teal-500/30 flex items-center justify-center shrink-0">
              <Smartphone className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm sm:text-base font-bold text-white flex items-center gap-2">
                Android Installation & Notification Guide
              </h3>
              <p className="text-[11px] sm:text-xs text-slate-400">
                How automatic bank notification recording works on your Android mobile
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition cursor-pointer"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Switcher - Fixed */}
        <div className="flex items-center gap-1.5 p-2 bg-slate-950 border-b border-slate-800 text-xs overflow-x-auto shrink-0 scrollbar-none">
          <button
            onClick={() => setActiveTab('how_it_works')}
            className={`py-2 px-3.5 rounded-xl font-bold whitespace-nowrap transition cursor-pointer ${
              activeTab === 'how_it_works'
                ? 'bg-teal-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            1. How Auto-Recording Works
          </button>
          <button
            onClick={() => setActiveTab('pwa_install')}
            className={`py-2 px-3.5 rounded-xl font-bold whitespace-nowrap transition cursor-pointer ${
              activeTab === 'pwa_install'
                ? 'bg-teal-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            2. Install as PWA (Fastest)
          </button>
          <button
            onClick={() => setActiveTab('native_apk')}
            className={`py-2 px-3.5 rounded-xl font-bold whitespace-nowrap transition cursor-pointer ${
              activeTab === 'native_apk'
                ? 'bg-teal-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            3. Build & Install Native APK
          </button>
          <button
            onClick={() => setActiveTab('permission')}
            className={`py-2 px-3.5 rounded-xl font-bold whitespace-nowrap transition cursor-pointer ${
              activeTab === 'permission'
                ? 'bg-teal-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            4. Grant Notification Access
          </button>
        </div>

        {/* Tab Content */}
        <div className="p-4 sm:p-6 overflow-y-auto flex-1 min-h-0 space-y-4 text-xs text-slate-300 leading-relaxed">
          {/* TAB 1: How Auto-Recording Works */}
          {activeTab === 'how_it_works' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-teal-950/30 border border-teal-500/30">
                <h4 className="text-sm font-bold text-white mb-1.5 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-teal-400" />
                  Android Notification Security Architecture
                </h4>
                <p className="text-teal-200">
                  On Android, third-party apps and browsers are sandboxed by the operating system. To automatically intercept incoming push notifications and SMS alerts from banks without you having to type anything, Android provides a dedicated system capability: the <strong>NotificationListenerService</strong>.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="w-7 h-7 rounded-lg bg-teal-500/20 text-teal-400 flex items-center justify-center font-bold text-xs mb-2">
                    1
                  </div>
                  <h5 className="font-bold text-white text-xs mb-1">Bank Sends Alert</h5>
                  <p className="text-[11px] text-slate-400">
                    When you tap your card at Carrefour or ENOC, or receive a salary deposit, Emirates NBD, Citi, FAB, or Mashreq triggers a push or SMS alert.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="w-7 h-7 rounded-lg bg-teal-500/20 text-teal-400 flex items-center justify-center font-bold text-xs mb-2">
                    2
                  </div>
                  <h5 className="font-bold text-white text-xs mb-1">Silent Interception</h5>
                  <p className="text-[11px] text-slate-400">
                    DirhamTrack's background service intercepts the notification, extracts the amount, currency, merchant/salary, and card number.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="w-7 h-7 rounded-lg bg-teal-500/20 text-teal-400 flex items-center justify-center font-bold text-xs mb-2">
                    3
                  </div>
                  <h5 className="font-bold text-white text-xs mb-1">Auto Categorized</h5>
                  <p className="text-[11px] text-slate-400">
                    The transaction is matched to your budgets, checks for international red flags, and is saved locally in SQLite on your phone.
                  </p>
                </div>
              </div>

              <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 text-xs">
                <span className="font-bold text-white block mb-1">Supported UAE Banks & Services:</span>
                <p className="text-slate-400">
                  Emirates NBD, Citi (Citibank UAE), Mashreq (Salary Deposits & Purchases), First Abu Dhabi Bank (FAB), Commercial Bank of Dubai (CBD), RAKBANK, and native Android SMS alerts.
                </p>
              </div>
            </div>
          )}

          {/* TAB 2: PWA Install */}
          {activeTab === 'pwa_install' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800">
                <h4 className="text-sm font-bold text-white mb-2">Method 1: Instant PWA Install (Recommended)</h4>
                <p className="text-slate-300 mb-3">
                  You can install DirhamTrack directly to your Android home screen right now without downloading Android Studio or SDKs:
                </p>
                <ol className="list-decimal list-inside space-y-2 text-slate-300">
                  <li>
                    Open this app URL in <strong>Google Chrome</strong> or <strong>Android Browser</strong> on your Android mobile.
                  </li>
                  <li>
                    Tap the <strong>"Install App"</strong> button in the top navigation bar (or open Chrome menu <span className="font-mono text-teal-300">⋮</span> and select <strong>"Add to Home screen" / "Install app"</strong>).
                  </li>
                  <li>
                    Tap <strong>Install</strong> when the system confirmation appears.
                  </li>
                  <li>
                    The <strong>DirhamTrack</strong> app icon will now appear in your Android app drawer and home screen. It opens in full-screen standalone mode with offline storage!
                  </li>
                </ol>

                {isInstallable && (
                  <div className="mt-4 pt-3 border-t border-slate-800 flex justify-end">
                    <button
                      onClick={install}
                      className="px-4 py-2 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-xl flex items-center gap-2"
                    >
                      <Download className="w-4 h-4" />
                      <span>Install PWA Now</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: Build & Install Native APK */}
          {activeTab === 'native_apk' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800">
                <h4 className="text-sm font-bold text-white mb-2">
                  Method 2: Compile & Run Native Android APK
                </h4>
                <p className="text-slate-300 mb-3">
                  For 24/7 background notification interception when the app is completely closed in RAM, you compile the native Kotlin service:
                </p>

                <div className="space-y-2.5">
                  <div className="p-3 bg-slate-900 rounded-xl border border-slate-800">
                    <span className="font-bold text-teal-400">Step 1: Open Project in Android Studio</span>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Open Android Studio, choose <strong>Open</strong>, and select the project repository. All Kotlin files (<code className="text-teal-300">BankNotificationListener.kt</code>), <code className="text-teal-300">AndroidManifest.xml</code>, and <code className="text-teal-300">build.gradle.kts</code> are pre-configured.
                    </p>
                  </div>

                  <div className="p-3 bg-slate-900 rounded-xl border border-slate-800">
                    <span className="font-bold text-teal-400">Step 2: Generate APK</span>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      In Android Studio top menu: Navigate to <strong>Build &gt; Build Bundle(s) / APK(s) &gt; Build APK(s)</strong>.
                      The APK is generated at: <code className="text-slate-200">app/build/outputs/apk/debug/app-debug.apk</code>.
                    </p>
                  </div>

                  <div className="p-3 bg-slate-900 rounded-xl border border-slate-800">
                    <span className="font-bold text-teal-400">Step 3: Transfer to Android Phone</span>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Transfer <code className="text-white font-mono">app-debug.apk</code> to your Android phone via USB, Google Drive, or WhatsApp, and tap to install.
                    </p>
                  </div>
                </div>

                <div className="mt-4 flex justify-between items-center pt-3 border-t border-slate-800">
                  <span className="text-[11px] text-slate-400">
                    Background listener runs silently on-device.
                  </span>
                  <button
                    onClick={onOpenCodeViewer}
                    className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-750 text-teal-300 text-xs font-semibold rounded-xl border border-slate-700"
                  >
                    View Background Service Engine
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: Grant Notification Access Permission */}
          {activeTab === 'permission' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-amber-950/30 border border-amber-500/30">
                <h4 className="text-sm font-bold text-amber-200 mb-1 flex items-center gap-2">
                  <Bell className="w-4 h-4 text-amber-400" />
                  Required: Enable Notification Access on Your Android Device
                </h4>
                <p className="text-amber-100/90 text-xs">
                  This 1-time setup allows the app to intercept bank transaction alerts safely:
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3">
                <div className="flex items-start gap-3">
                  <span className="w-6 h-6 rounded-full bg-teal-500/20 text-teal-400 font-bold flex items-center justify-center shrink-0">1</span>
                  <div>
                    <p className="font-bold text-white">Open Android Settings</p>
                    <p className="text-slate-400 text-[11px]">Go to your device's <strong>Settings</strong> app.</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <span className="w-6 h-6 rounded-full bg-teal-500/20 text-teal-400 font-bold flex items-center justify-center shrink-0">2</span>
                  <div>
                    <p className="font-bold text-white">Navigate to Special App Access</p>
                    <p className="text-slate-400 text-[11px]">
                      Tap <strong>Apps</strong> (or <strong>Apps &amp; Notifications</strong>) &gt; <strong>Special app access</strong>. (Or simply type <em>"Notification access"</em> in the settings search bar).
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <span className="w-6 h-6 rounded-full bg-teal-500/20 text-teal-400 font-bold flex items-center justify-center shrink-0">3</span>
                  <div>
                    <p className="font-bold text-white">Enable DirhamTrack</p>
                    <p className="text-slate-400 text-[11px]">
                      Find <strong>DirhamTrack</strong> in the list and toggle the switch to <strong>ON</strong>.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <span className="w-6 h-6 rounded-full bg-teal-500/20 text-teal-400 font-bold flex items-center justify-center shrink-0">4</span>
                  <div>
                    <p className="font-bold text-white">Confirmation &amp; Active Status</p>
                    <p className="text-slate-400 text-[11px]">
                      Tap <strong>Allow</strong> on the Android system prompt. Now, whenever an alert arrives from your UAE bank or SMS, it will be automatically recorded!
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-3.5 sm:p-4 bg-slate-950 border-t border-slate-800 flex items-center justify-between gap-3 shrink-0">
          <button
            onClick={onClose}
            className="flex-1 sm:flex-none px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white font-semibold text-xs rounded-xl border border-slate-700 transition cursor-pointer text-center"
          >
            Cancel
          </button>
          <button
            onClick={onClose}
            className="flex-1 sm:flex-none px-5 py-2 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-xl transition cursor-pointer text-center"
          >
            Got It
          </button>
        </div>
      </div>
    </div>
  );
};
