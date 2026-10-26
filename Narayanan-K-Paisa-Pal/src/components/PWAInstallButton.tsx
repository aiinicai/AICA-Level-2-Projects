import React, { useState, useEffect } from 'react';
import {
  Download,
  CheckCircle,
  Share,
  PlusSquare,
  Smartphone,
  Laptop,
  X,
  ExternalLink,
  Copy,
  Check,
  QrCode,
  Info,
} from 'lucide-react';
import QRCode from 'qrcode';
import { usePWAInstall } from '../hooks/usePWAInstall';

interface Props {
  variant?: 'compact' | 'full' | 'nav';
}

export const PWAInstallButton: React.FC<Props> = ({ variant = 'compact' }) => {
  const { isInstallable, isInstalled, isIOS, isInIframe, install } =
    usePWAInstall();
  const [showGuide, setShowGuide] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [qrDataUrl, setQrDataUrl] = useState<string>('');
  const [activeDeviceTab, setActiveDeviceTab] = useState<'android' | 'ios' | 'pc'>(
    isIOS ? 'ios' : 'android'
  );

  const currentUrl = typeof window !== 'undefined' ? window.location.href : '';

  useEffect(() => {
    if (showGuide && currentUrl) {
      QRCode.toDataURL(currentUrl, {
        width: 180,
        margin: 1,
        color: {
          dark: '#0B3B66',
          light: '#FFFFFF',
        },
      })
        .then((url) => setQrDataUrl(url))
        .catch((err) => console.error('QR code generation failed', err));
    }
  }, [showGuide, currentUrl]);

  // If already running inside standalone PWA window, display an installed badge or suppress
  if (isInstalled) {
    if (variant === 'nav') {
      return (
        <div className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-300 bg-emerald-950/40 rounded-lg border border-emerald-800/40">
          <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
          <span>App Installed</span>
        </div>
      );
    }
    return null;
  }

  const handleInstallClick = async () => {
    if (isInstallable) {
      const res = await install();
      if (!res) {
        setShowGuide(true);
      }
    } else {
      setShowGuide(true);
    }
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(currentUrl);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  };

  const buttonContent = (
    <>
      <Download className="w-4 h-4 flex-shrink-0" />
      <span>{isIOS ? 'Install on iPhone' : 'Install App'}</span>
    </>
  );

  return (
    <>
      {variant === 'nav' ? (
        <button
          onClick={handleInstallClick}
          className="flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg bg-[#0E7C86] hover:bg-[#128e9a] text-white transition-all shadow-sm w-full justify-center"
          title="Install Paisa Pal as a desktop or mobile application"
        >
          {buttonContent}
        </button>
      ) : variant === 'full' ? (
        <button
          onClick={handleInstallClick}
          className="flex items-center gap-2.5 px-4 py-2.5 text-sm font-semibold rounded-xl bg-[#0E7C86] hover:bg-[#128e9a] text-white shadow-sm transition active:scale-[0.98]"
        >
          {buttonContent}
        </button>
      ) : (
        <button
          onClick={handleInstallClick}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-[#DCE2EA] dark:border-[#25324A] bg-[#FFFFFF] dark:bg-[#131C2E] hover:border-[#0E7C86] text-[#0F1B2D] dark:text-[#E8EDF5] transition"
        >
          {buttonContent}
        </button>
      )}

      {/* Installation Guide & QR Code Modal */}
      {showGuide && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-3 sm:p-4 overflow-y-auto"
        >
          <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl max-w-lg w-full p-5 sm:p-6 shadow-2xl relative text-[#0F1B2D] dark:text-[#E8EDF5] max-h-[92vh] flex flex-col">
            <button
              onClick={() => setShowGuide(false)}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
              aria-label="Close installation guide"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-[#0E7C86]/10 text-[#0E7C86] flex items-center justify-center font-bold flex-shrink-0">
                <Smartphone className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-lg leading-tight">Install Paisa Pal</h3>
                <p className="text-xs text-[#6F7E92] dark:text-[#8594AA]">
                  Free, offline-ready application for your Phone & Computer
                </p>
              </div>
            </div>

            {/* Why browser shows "Install Google AI Studio" */}
            <div className="mb-4 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800/80 p-3.5 rounded-xl text-xs space-y-2.5">
              <div className="font-bold text-amber-900 dark:text-amber-200 flex items-center gap-1.5 text-xs">
                <Info className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0" />
                <span>Seeing &ldquo;Install Google AI Studio&rdquo; instead?</span>
              </div>
              <p className="text-amber-900/90 dark:text-amber-200/90 leading-relaxed text-[11px] sm:text-xs">
                Your browser&rsquo;s address bar currently holds Google AI Studio&rsquo;s URL. Chrome and Edge see the outer developer workspace, not the embedded preview frame.
              </p>
              <div className="pt-1 flex flex-col sm:flex-row gap-2">
                <a
                  href={currentUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 bg-[#0E7C86] hover:bg-[#128e9a] text-white font-semibold rounded-lg text-xs transition shadow-xs text-center"
                >
                  <ExternalLink className="w-4 h-4" />
                  <span>1. Open Standalone Tab</span>
                </a>
                <button
                  type="button"
                  onClick={handleCopyLink}
                  className="flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg border border-amber-300 dark:border-amber-700 bg-white dark:bg-[#131C2E] text-amber-900 dark:text-amber-200 font-medium text-xs hover:bg-amber-100/50 transition"
                >
                  {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-amber-600" />}
                  <span>{copiedLink ? 'Copied!' : 'Copy Direct Link'}</span>
                </button>
              </div>
              <p className="text-[11px] text-amber-800/80 dark:text-amber-300/80 italic">
                In the new standalone tab, the browser install button will properly say <strong>&ldquo;Install Paisa Pal&rdquo;</strong>.
              </p>
            </div>

            {/* Device Tabs */}
            <div className="grid grid-cols-3 gap-1.5 p-1 bg-[#EEF1F5] dark:bg-[#0B1220] rounded-xl text-xs font-semibold mb-3">
              <button
                type="button"
                onClick={() => setActiveDeviceTab('android')}
                className={`py-1.5 rounded-lg transition ${
                  activeDeviceTab === 'android'
                    ? 'bg-white dark:bg-[#131C2E] text-[#0E7C86] shadow-xs'
                    : 'text-[#6F7E92] dark:text-[#8594AA]'
                }`}
              >
                Android Phone
              </button>
              <button
                type="button"
                onClick={() => setActiveDeviceTab('ios')}
                className={`py-1.5 rounded-lg transition ${
                  activeDeviceTab === 'ios'
                    ? 'bg-white dark:bg-[#131C2E] text-[#0E7C86] shadow-xs'
                    : 'text-[#6F7E92] dark:text-[#8594AA]'
                }`}
              >
                Apple iPhone
              </button>
              <button
                type="button"
                onClick={() => setActiveDeviceTab('pc')}
                className={`py-1.5 rounded-lg transition ${
                  activeDeviceTab === 'pc'
                    ? 'bg-white dark:bg-[#131C2E] text-[#0E7C86] shadow-xs'
                    : 'text-[#6F7E92] dark:text-[#8594AA]'
                }`}
              >
                Windows / Mac
              </button>
            </div>

            {/* Tab Contents */}
            <div className="overflow-y-auto flex-1 text-xs space-y-3">
              {activeDeviceTab === 'android' && (
                <div className="space-y-2.5">
                  <div className="bg-[#EEF1F5] dark:bg-[#0B1220] p-3.5 rounded-xl space-y-2">
                    <strong className="text-xs text-[#0F1B2D] dark:text-[#E8EDF5] block">
                      Instructions for Android (Chrome or Edge):
                    </strong>
                    <ol className="list-decimal list-inside space-y-1.5 text-xs text-[#46566C] dark:text-[#A9B6C9] leading-relaxed">
                      <li>Open this app address in <strong>Google Chrome</strong> on your phone.</li>
                      <li>Tap the <strong>three dots (⋮)</strong> at the top right of Chrome.</li>
                      <li>Tap <strong>Install app</strong> or <strong>Add to Home screen</strong>.</li>
                      <li>Tap <strong>Install</strong> to confirm. The Paisa Pal icon will appear alongside your other phone apps!</li>
                    </ol>
                  </div>

                  {qrDataUrl && (
                    <div className="flex items-center gap-3 p-3 bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl">
                      <img
                        src={qrDataUrl}
                        alt="Scan QR code to install on phone"
                        className="w-20 h-20 rounded-lg border border-slate-200 dark:border-slate-700 bg-white p-1"
                      />
                      <div className="text-xs">
                        <strong className="block text-[#0F1B2D] dark:text-[#E8EDF5]">
                          Scan with phone camera
                        </strong>
                        <p className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] mt-0.5">
                          Point your Android phone camera at this QR code to open and install Paisa Pal immediately.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeDeviceTab === 'ios' && (
                <div className="space-y-2.5">
                  <div className="bg-[#EEF1F5] dark:bg-[#0B1220] p-3.5 rounded-xl space-y-2">
                    <strong className="text-xs text-[#0F1B2D] dark:text-[#E8EDF5] block">
                      Instructions for Apple iPhone & iPad (Safari):
                    </strong>
                    <ol className="list-decimal list-inside space-y-2 text-xs text-[#46566C] dark:text-[#A9B6C9] leading-relaxed">
                      <li>
                        Open this link in <strong>Safari</strong> (Apple requires Safari for home screen install).
                      </li>
                      <li>
                        Tap the <strong>Share</strong> button (
                        <Share className="inline w-3.5 h-3.5 mx-0.5 text-[#0E7C86]" />
                        box with arrow pointing up) at the bottom toolbar.
                      </li>
                      <li>
                        Scroll down and tap <strong>Add to Home Screen</strong> (
                        <PlusSquare className="inline w-3.5 h-3.5 mx-0.5 text-[#0E7C86]" />
                        plus icon).
                      </li>
                      <li>
                        Tap <strong>Add</strong> in the top right. Paisa Pal is now installed on your iPhone home screen!
                      </li>
                    </ol>
                  </div>

                  {qrDataUrl && (
                    <div className="flex items-center gap-3 p-3 bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl">
                      <img
                        src={qrDataUrl}
                        alt="Scan QR code with iPhone camera"
                        className="w-20 h-20 rounded-lg border border-slate-200 dark:border-slate-700 bg-white p-1"
                      />
                      <div className="text-xs">
                        <strong className="block text-[#0F1B2D] dark:text-[#E8EDF5]">
                          Scan with iPhone camera
                        </strong>
                        <p className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] mt-0.5">
                          Point your iPhone Camera at this code, then tap the yellow Safari banner to open and install.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeDeviceTab === 'pc' && (
                <div className="space-y-3">
                  <div className="bg-[#EEF1F5] dark:bg-[#0B1220] p-3.5 rounded-xl space-y-2">
                    <strong className="text-xs text-[#0F1B2D] dark:text-[#E8EDF5] block">
                      Option A: Standard PWA App Install
                    </strong>
                    <ol className="list-decimal list-inside space-y-1.5 text-xs text-[#46566C] dark:text-[#A9B6C9] leading-relaxed">
                      <li>First, click <strong>&ldquo;Open in Tab&rdquo;</strong> below so you are on the app&rsquo;s direct URL (not Google AI Studio).</li>
                      <li>Look at the right end of the address URL bar for the <strong>Install icon</strong> (computer monitor with a down arrow).</li>
                      <li>Click <strong>Install Paisa Pal</strong>. It creates a desktop icon and taskbar shortcut that launches in its own window!</li>
                    </ol>
                  </div>

                  <div className="bg-sky-50 dark:bg-sky-950/40 border border-sky-200 dark:border-sky-900/50 p-3.5 rounded-xl space-y-2">
                    <strong className="text-xs text-sky-900 dark:text-sky-200 block">
                      Option B: Alternate Shortcut (No PWA prompt required)
                    </strong>
                    <ol className="list-decimal list-inside space-y-1.5 text-xs text-sky-950/80 dark:text-sky-200/80 leading-relaxed">
                      <li>In Chrome/Edge on the opened tab, click the <strong>3 dots (⋮)</strong> at the top right.</li>
                      <li>Hover over <strong>Save and share</strong> (or <strong>More tools</strong>) &rarr; click <strong>Create shortcut...</strong></li>
                      <li>Check the box <strong>&ldquo;Open as window&rdquo;</strong> and click <strong>Create</strong>.</li>
                      <li>This creates an instant desktop window app without needing any PWA prompt!</li>
                    </ol>
                  </div>

                  <div className="bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/50 p-3 rounded-xl text-xs text-emerald-900 dark:text-emerald-200 flex items-start gap-2">
                    <Check className="w-4 h-4 text-emerald-600 dark:text-emerald-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <strong>Option C: Direct Browser Use (100% Offline Ready)</strong>
                      <p className="text-[11px] text-emerald-800/80 dark:text-emerald-300/80 mt-0.5">
                        No install required! Simply press <strong>Ctrl+D</strong> (or <strong>Cmd+D</strong> on Mac) to bookmark the tab. All your data and document attachments stay securely in your browser&rsquo;s local database.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Quick Actions Footer */}
            <div className="mt-4 pt-3 border-t border-[#DCE2EA] dark:border-[#25324A] flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopyLink}
                className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl border border-[#DCE2EA] dark:border-[#25324A] text-xs font-medium hover:bg-slate-50 dark:hover:bg-slate-800 transition"
              >
                {copiedLink ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Link Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 text-slate-500" />
                    <span>Copy Direct Link</span>
                  </>
                )}
              </button>

              <a
                href={currentUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-[#0E7C86] hover:bg-[#128e9a] text-white text-xs font-semibold transition text-center shadow-xs"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>Open in Tab</span>
              </a>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
