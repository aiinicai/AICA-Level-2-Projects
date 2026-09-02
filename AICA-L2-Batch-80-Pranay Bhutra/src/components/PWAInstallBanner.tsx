import React, { useState, useEffect } from 'react';
import {
  Smartphone,
  Download,
  X,
  CheckCircle2,
  Wifi,
  ShieldCheck,
  Sparkles,
  Layers
} from 'lucide-react';
import { AppLogo } from './AppLogo';
import { ThemeStyle, IconConcept } from '../types';

interface PWAInstallBannerProps {
  isOpen: boolean;
  onClose: () => void;
  currentTheme: ThemeStyle;
  currentIcon: IconConcept;
}

export const PWAInstallBanner: React.FC<PWAInstallBannerProps> = ({
  isOpen,
  onClose,
  currentTheme,
  currentIcon,
}) => {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [isInstalled, setIsInstalled] = useState(false);
  const [showManualInstructions, setShowManualInstructions] = useState(false);

  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    if (window.matchMedia('(display-mode: standalone)').matches) {
      setIsInstalled(true);
    }

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  const handleInstallClick = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === 'accepted') {
        setIsInstalled(true);
      }
      setDeferredPrompt(null);
    } else {
      setShowManualInstructions(true);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <Smartphone className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                PWA On-The-Go Mobile Access
                <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Ready
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Install as a native standalone app on iOS, Android, or Desktop.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="py-4 space-y-4 text-xs">
          <div className="flex items-center justify-center py-3 bg-slate-950/80 rounded-xl border border-slate-800">
            <AppLogo concept={currentIcon} themeStyle={currentTheme} size="lg" showText={true} />
          </div>

          <div className="space-y-2.5">
            <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950 border border-slate-800/80">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-slate-200 block">Instant Front-Desk & Field Logging:</span>
                <span className="text-slate-400 text-[11px]">
                  Reception tablet mount or field staff smartphone camera scanner for instant POD uploads.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950 border border-slate-800/80">
              <Wifi className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-slate-200 block">Offline Cache Resilience:</span>
                <span className="text-slate-400 text-[11px]">
                  Works seamlessly in office basements, archives, or during spotty client site network drops.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950 border border-slate-800/80">
              <ShieldCheck className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-slate-200 block">Role-Based Security:</span>
                <span className="text-slate-400 text-[11px]">
                  Each article assistant and partner accesses their respective assigned dispatches securely.
                </span>
              </div>
            </div>
          </div>
          {showManualInstructions && (
            <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-300 text-xs space-y-1 animate-in fade-in">
              <span className="font-bold text-white block">Manual Installation Instructions:</span>
              <p className="text-slate-300 text-[11px] leading-relaxed">
                • <strong>iOS / Safari:</strong> Tap the <span className="font-semibold text-blue-400">Share</span> icon (square with arrow) ➔ select <span className="font-semibold text-blue-400">"Add to Home Screen"</span>.
              </p>
              <p className="text-slate-300 text-[11px] leading-relaxed">
                • <strong>Chrome / Android / Desktop:</strong> Click the browser menu (⋮) ➔ select <span className="font-semibold text-blue-400">"Install app"</span> or <span className="font-semibold text-blue-400">"Install ParcelDesk"</span>.
              </p>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
          >
            Dismiss
          </button>

          <button
            onClick={handleInstallClick}
            className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition-all shadow-lg shadow-blue-600/30 flex items-center gap-1.5"
          >
            <Download className="w-4 h-4" />
            <span>{isInstalled ? 'App Already Installed' : 'Add to Home Screen / Install'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
