import React from 'react';
import { 
  X, Smartphone, Monitor, Apple, CheckCircle2, 
  ArrowRight, Download, Share2, PlusSquare
} from 'lucide-react';

interface InstallAppModalProps {
  onClose: () => void;
  deferredPrompt?: any;
}

export const InstallAppModal: React.FC<InstallAppModalProps> = ({ onClose, deferredPrompt }) => {
  const [activePlatform, setActivePlatform] = React.useState<'desktop' | 'ios' | 'android'>('desktop');

  const handleNativeInstall = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const choiceResult = await deferredPrompt.userChoice;
      if (choiceResult.outcome === 'accepted') {
        onClose();
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-slate-200 animate-in fade-in space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-brand-50 text-brand-800 rounded-lg">
              <Download className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-sm">Install GIA_Arthwise Loan Syndication App</h3>
              <p className="text-xs text-slate-500">Standalone Progressive Web App (PWA) with Dock & Home Screen Launch</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 1-Click Native Install if Supported */}
        {deferredPrompt && (
          <div className="p-3 bg-brand-50 border border-brand-200 rounded-xl flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-brand-900">Browser Ready for 1-Click Install</p>
              <p className="text-[11px] text-brand-700">Add directly to your Applications folder / Dock</p>
            </div>
            <button
              onClick={handleNativeInstall}
              className="px-4 py-2 bg-brand-800 hover:bg-brand-900 text-white rounded-lg text-xs font-bold shadow-sm transition-all"
            >
              Install Now
            </button>
          </div>
        )}

        {/* Platform Selector */}
        <div className="flex rounded-lg bg-slate-100 p-1 text-xs font-semibold">
          <button
            onClick={() => setActivePlatform('desktop')}
            className={`flex-1 py-1.5 flex items-center justify-center gap-1.5 rounded-md transition-all ${
              activePlatform === 'desktop' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <Monitor className="w-3.5 h-3.5" />
            <span>Mac & PC Desktop</span>
          </button>
          <button
            onClick={() => setActivePlatform('ios')}
            className={`flex-1 py-1.5 flex items-center justify-center gap-1.5 rounded-md transition-all ${
              activePlatform === 'ios' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <Apple className="w-3.5 h-3.5" />
            <span>iPhone / iPad (iOS)</span>
          </button>
          <button
            onClick={() => setActivePlatform('android')}
            className={`flex-1 py-1.5 flex items-center justify-center gap-1.5 rounded-md transition-all ${
              activePlatform === 'android' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <Smartphone className="w-3.5 h-3.5" />
            <span>Android Phone</span>
          </button>
        </div>

        {/* Platform Steps */}
        <div className="text-xs space-y-3 p-4 rounded-xl bg-slate-50 border border-slate-200">
          {activePlatform === 'desktop' && (
            <div className="space-y-2.5">
              <div className="flex items-start gap-2.5">
                <span className="w-5 h-5 rounded-full bg-brand-800 text-white flex items-center justify-center font-bold text-[10px] flex-shrink-0 mt-0.5">1</span>
                <div>
                  <strong>Look at your browser's address bar</strong> (right side near the bookmark star icon in Chrome, Edge, or Brave).
                </div>
              </div>
              <div className="flex items-start gap-2.5">
                <span className="w-5 h-5 rounded-full bg-brand-800 text-white flex items-center justify-center font-bold text-[10px] flex-shrink-0 mt-0.5">2</span>
                <div>
                  Click the <strong>"Install app"</strong> icon (a small computer monitor or download symbol).
                </div>
              </div>
              <div className="flex items-start gap-2.5">
                <span className="w-5 h-5 rounded-full bg-brand-800 text-white flex items-center justify-center font-bold text-[10px] flex-shrink-0 mt-0.5">3</span>
                <div>
                  Click <strong>"Install"</strong> in the popup prompt. The app will launch in its own dedicated, distraction-free native macOS window and be added to your Launchpad and Dock!
                </div>
              </div>
            </div>
          )}

          {activePlatform === 'ios' && (
            <div className="space-y-2.5">
              <div className="flex items-start gap-2.5">
                <span className="w-5 h-5 rounded-full bg-brand-800 text-white flex items-center justify-center font-bold text-[10px] flex-shrink-0 mt-0.5">1</span>
                <div>
                  Open <strong>Safari</strong> on your iPhone or iPad and navigate to your server address.
                </div>
              </div>
              <div className="flex items-start gap-2.5">
                <span className="w-5 h-5 rounded-full bg-brand-800 text-white flex items-center justify-center font-bold text-[10px] flex-shrink-0 mt-0.5">2</span>
                <div>
                  Tap the <strong>Share</strong> button <Share2 className="w-3.5 h-3.5 inline mx-1 text-sky-600" /> at the bottom of Safari.
                </div>
              </div>
              <div className="flex items-start gap-2.5">
                <span className="w-5 h-5 rounded-full bg-brand-800 text-white flex items-center justify-center font-bold text-[10px] flex-shrink-0 mt-0.5">3</span>
                <div>
                  Scroll down the share sheet and tap <strong>"Add to Home Screen"</strong> <PlusSquare className="w-3.5 h-3.5 inline mx-1 text-slate-700" />, then tap <strong>Add</strong> in the top right.
                </div>
              </div>
            </div>
          )}

          {activePlatform === 'android' && (
            <div className="space-y-3">
              <div className="p-3 bg-brand-50 border border-brand-200 rounded-lg text-xs space-y-1.5">
                <p className="font-bold text-brand-900">Recommended Method: 1-Click WebAPK via Chrome</p>
                <p className="text-slate-600">
                  Google Chrome automatically mints, signs, and installs a native Android APK directly on your phone with full home screen and app drawer integration.
                </p>
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-start gap-2">
                    <span className="w-4 h-4 rounded-full bg-brand-800 text-white flex items-center justify-center font-bold text-[9px] flex-shrink-0 mt-0.5">1</span>
                    <span>Open <strong>Google Chrome</strong> on your phone and browse to your server URL.</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="w-4 h-4 rounded-full bg-brand-800 text-white flex items-center justify-center font-bold text-[9px] flex-shrink-0 mt-0.5">2</span>
                    <span>Tap the <strong>three dots (⋮)</strong> menu in the upper right.</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="w-4 h-4 rounded-full bg-brand-800 text-white flex items-center justify-center font-bold text-[9px] flex-shrink-0 mt-0.5">3</span>
                    <span>Tap <strong>"Install app"</strong> (or "Add to Home screen") and tap <strong>Install</strong>.</span>
                  </div>
                </div>
              </div>

              <div className="p-3 bg-slate-100/80 border border-slate-200 rounded-lg text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">Alternative: Standalone APK Package</span>
                  <a
                    href="/download/app.apk"
                    download="giaarthwise-loan-facilitator.apk"
                    className="px-2.5 py-1 bg-brand-800 hover:bg-brand-900 text-white text-[11px] font-semibold rounded shadow-xs"
                  >
                    Download .APK
                  </a>
                </div>
                <p className="text-[11px] text-slate-500">
                  A complete native Android project is included in <code>android/</code> with a 1-click build script: <code>./android/build_apk.sh</code>.
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="pt-2 flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 hover:bg-black text-white rounded-lg text-xs font-semibold"
          >
            Got It
          </button>
        </div>
      </div>
    </div>
  );
};
