import React, { useState, useEffect } from 'react';
import {
  X,
  Share2,
  Copy,
  Check,
  Smartphone,
  Laptop,
  MessageCircle,
  Mail,
  ExternalLink,
  ShieldCheck,
  Sparkles,
  QrCode,
  AlertCircle,
  HelpCircle,
  Compass,
} from 'lucide-react';
import QRCode from 'qrcode';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onNotify?: (msg: string) => void;
}

export const SHARED_APP_URL =
  'https://ais-pre-fmrljjhfbcr77w27rsoewt-472756614252.asia-southeast1.run.app';

export const DEV_APP_URL =
  'https://ais-dev-fmrljjhfbcr77w27rsoewt-472756614252.asia-southeast1.run.app';

export const ShareTrialModal: React.FC<Props> = ({ isOpen, onClose, onNotify }) => {
  const [copied, setCopied] = useState(false);
  const [qrCodeUrl, setQrCodeUrl] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'quick' | 'iphone' | 'qr' | 'guide'>('quick');
  const [urlType, setUrlType] = useState<'shared' | 'dev'>('shared');

  const trialUrl = urlType === 'shared' ? SHARED_APP_URL : DEV_APP_URL;

  const invitationMessage = `Hi! Take a look at Paisa Pal — a private family financial vault for tracking investments (FD, PPF, SIP, Gold), bill due dates, policy renewals, and emergency records.

Try it out here (works on iPhone, Android, and Desktop):
${trialUrl}

Tip: On the home screen, tap "Load Sample Data" to test all portfolio analytics with realistic sample entries!`;

  useEffect(() => {
    if (isOpen) {
      QRCode.toDataURL(trialUrl, {
        width: 220,
        margin: 1.5,
        color: {
          dark: '#0F2A47',
          light: '#FFFFFF',
        },
      })
        .then((url) => setQrCodeUrl(url))
        .catch((err) => console.error('Failed to generate QR code', err));
    }
  }, [isOpen, trialUrl]);

  if (!isOpen) return null;

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(trialUrl);
      setCopied(true);
      if (onNotify) onNotify('Link copied to clipboard!');
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const handleCopyFullInvite = async () => {
    try {
      await navigator.clipboard.writeText(invitationMessage);
      setCopied(true);
      if (onNotify) onNotify('Full invite message copied to clipboard!');
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const handleWhatsAppShare = () => {
    const encoded = encodeURIComponent(invitationMessage);
    const whatsappUrl = `https://api.whatsapp.com/send?text=${encoded}`;
    window.open(whatsappUrl, '_blank', 'noopener,noreferrer');
  };

  const handleEmailShare = () => {
    const subject = encodeURIComponent('Try Paisa Pal - Family Finance & Due Vault');
    const body = encodeURIComponent(invitationMessage);
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
  };

  const handleNativeShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'Paisa Pal - Family Finance & Due Vault',
          text: 'Private family financial vault for tracking investments, bill due dates, and emergency records.',
          url: trialUrl,
        });
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          handleCopyLink();
        }
      }
    } else {
      handleCopyLink();
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-3 sm:p-4 overflow-y-auto"
    >
      <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl max-w-lg w-full p-5 sm:p-6 shadow-2xl relative text-[#0F1B2D] dark:text-[#E8EDF5] max-h-[94vh] flex flex-col">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
          aria-label="Close"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-[#0E7C86]/10 text-[#0E7C86] flex items-center justify-center font-bold flex-shrink-0">
            <Share2 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-bold text-lg leading-tight">Send for Trial</h2>
            <p className="text-xs text-[#6F7E92] dark:text-[#8594AA]">
              Share Paisa Pal on iPhone, Android, or Desktop
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="grid grid-cols-4 gap-1 p-1 bg-[#EEF1F5] dark:bg-[#0B1220] rounded-xl text-xs font-semibold mb-3">
          <button
            type="button"
            onClick={() => setActiveTab('quick')}
            className={`py-1.5 px-2 rounded-lg transition text-center truncate ${
              activeTab === 'quick'
                ? 'bg-white dark:bg-[#131C2E] text-[#0E7C86] shadow-xs'
                : 'text-[#6F7E92] dark:text-[#8594AA]'
            }`}
          >
            Quick Share
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('iphone')}
            className={`py-1.5 px-2 rounded-lg transition text-center truncate flex items-center justify-center gap-1 ${
              activeTab === 'iphone'
                ? 'bg-white dark:bg-[#131C2E] text-amber-600 dark:text-amber-400 shadow-xs'
                : 'text-amber-700 dark:text-amber-300'
            }`}
          >
            <Smartphone className="w-3.5 h-3.5" />
            <span>iPhone Fix</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('qr')}
            className={`py-1.5 px-2 rounded-lg transition text-center truncate ${
              activeTab === 'qr'
                ? 'bg-white dark:bg-[#131C2E] text-[#0E7C86] shadow-xs'
                : 'text-[#6F7E92] dark:text-[#8594AA]'
            }`}
          >
            QR Code
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('guide')}
            className={`py-1.5 px-2 rounded-lg transition text-center truncate ${
              activeTab === 'guide'
                ? 'bg-white dark:bg-[#131C2E] text-[#0E7C86] shadow-xs'
                : 'text-[#6F7E92] dark:text-[#8594AA]'
            }`}
          >
            How it works
          </button>
        </div>

        {/* Scrollable Tab Body */}
        <div className="overflow-y-auto flex-1 space-y-3.5 text-xs pr-0.5">
          {activeTab === 'quick' && (
            <div className="space-y-3.5">
              {/* iPhone Alert Banner */}
              <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800/80 p-3 rounded-xl text-amber-950 dark:text-amber-200 space-y-1.5">
                <div className="flex items-center justify-between font-bold text-xs">
                  <span className="flex items-center gap-1.5">
                    <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0" />
                    Opening on an iPhone?
                  </span>
                  <button
                    onClick={() => setActiveTab('iphone')}
                    className="underline text-[11px] text-[#0E7C86] dark:text-[#3CB7C2] font-semibold"
                  >
                    View iPhone Guide &rarr;
                  </button>
                </div>
                <p className="text-[11px] leading-relaxed text-amber-900/90 dark:text-amber-200/90">
                  If you see a <strong>404 error</strong> or blank screen on iPhone, the link must be activated via the blue <strong>&ldquo;Share&rdquo;</strong> button in Google AI Studio, or opened directly in <strong>Safari</strong> (not WhatsApp&rsquo;s mini-browser).
                </p>
              </div>

              {/* URL Mode Toggle */}
              <div className="flex items-center justify-between bg-[#F8FAFC] dark:bg-[#0A1626] p-2 rounded-xl border border-[#DCE2EA] dark:border-[#25324A]">
                <span className="text-[11px] font-semibold text-[#46566C] dark:text-[#A9B6C9]">
                  Select Link Target:
                </span>
                <div className="flex gap-1">
                  <button
                    onClick={() => setUrlType('shared')}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition ${
                      urlType === 'shared'
                        ? 'bg-[#0E7C86] text-white shadow-xs'
                        : 'text-[#6F7E92] hover:bg-slate-200 dark:hover:bg-slate-800'
                    }`}
                  >
                    Public Shared Link
                  </button>
                  <button
                    onClick={() => setUrlType('dev')}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition ${
                      urlType === 'dev'
                        ? 'bg-[#0E7C86] text-white shadow-xs'
                        : 'text-[#6F7E92] hover:bg-slate-200 dark:hover:bg-slate-800'
                    }`}
                  >
                    Owner Dev Link
                  </button>
                </div>
              </div>

              {/* Direct URL Box */}
              <div>
                <label className="block text-[11px] font-semibold text-[#6F7E92] dark:text-[#8594AA] uppercase tracking-wider mb-1.5">
                  {urlType === 'shared' ? 'Public Shared App URL (For Friends & Family)' : 'Direct Dev Link (Requires Google Account Sign-In)'}
                </label>
                <div className="flex items-center gap-2 p-2.5 rounded-xl border border-[#DCE2EA] dark:border-[#25324A] bg-[#F8FAFC] dark:bg-[#0A1626]">
                  <input
                    type="text"
                    readOnly
                    value={trialUrl}
                    className="w-full bg-transparent text-xs font-mono text-[#0F1B2D] dark:text-[#E8EDF5] focus:outline-hidden select-all"
                    onClick={(e) => (e.target as HTMLInputElement).select()}
                  />
                  <button
                    onClick={handleCopyLink}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0E7C86] hover:bg-[#128e9a] text-white font-medium text-xs flex-shrink-0 transition shadow-xs"
                    title="Copy URL"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3.5 h-3.5" />
                        <span>Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Instant Share Buttons */}
              <div className="space-y-2">
                <label className="block text-[11px] font-semibold text-[#6F7E92] dark:text-[#8594AA] uppercase tracking-wider">
                  1-Click Send Options
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <button
                    onClick={handleWhatsAppShare}
                    className="flex items-center justify-center gap-2 py-2.5 px-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold transition shadow-xs"
                  >
                    <MessageCircle className="w-4 h-4" />
                    <span>Send via WhatsApp</span>
                  </button>

                  <button
                    onClick={handleEmailShare}
                    className="flex items-center justify-center gap-2 py-2.5 px-3.5 rounded-xl bg-[#0B3B66] hover:bg-[#104a80] text-white font-semibold transition shadow-xs"
                  >
                    <Mail className="w-4 h-4" />
                    <span>Send via Email</span>
                  </button>
                </div>

                <div className="flex gap-2 pt-1">
                  <button
                    onClick={handleCopyFullInvite}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl border border-[#DCE2EA] dark:border-[#25324A] bg-white dark:bg-[#131C2E] hover:bg-slate-50 dark:hover:bg-slate-800 text-[#0F1B2D] dark:text-[#E8EDF5] font-medium transition"
                  >
                    <Copy className="w-3.5 h-3.5 text-[#0E7C86]" />
                    <span>Copy Full Invite Text</span>
                  </button>

                  <a
                    href={trialUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl border border-[#DCE2EA] dark:border-[#25324A] bg-white dark:bg-[#131C2E] hover:bg-slate-50 dark:hover:bg-slate-800 text-[#0F1B2D] dark:text-[#E8EDF5] font-medium transition"
                    title="Open in new window"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>Test Link</span>
                  </a>
                </div>
              </div>

              {/* Sample Data Tip */}
              <div className="bg-sky-50 dark:bg-sky-950/40 border border-sky-200 dark:border-sky-900/50 p-3 rounded-xl space-y-1.5 text-sky-900 dark:text-sky-200">
                <div className="font-semibold flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-sky-600 dark:text-sky-400" />
                  <span>Tip for whoever tests it:</span>
                </div>
                <p className="text-[11px] leading-relaxed text-sky-950/80 dark:text-sky-200/80">
                  Tell them to tap <strong>&ldquo;Load Sample Data&rdquo;</strong> on the home dashboard. This fills the app with demo FDs, insurance policies, and bills so they can test charts and alerts immediately!
                </p>
              </div>
            </div>
          )}

          {/* Dedicated iPhone Troubleshooting Tab */}
          {activeTab === 'iphone' && (
            <div className="space-y-3">
              <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800/80 p-3.5 rounded-xl space-y-2">
                <strong className="text-xs text-amber-950 dark:text-amber-200 block font-bold flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4 text-amber-600" />
                  Why is the link not opening on iPhone? (Fix Checklist)
                </strong>
                <p className="text-[11px] text-amber-900/90 dark:text-amber-300/90 leading-relaxed">
                  Apple iPhones use Safari&rsquo;s security engine and handle links differently than Android and Desktop:
                </p>
              </div>

              {/* Reason 1: Shared App URL 404 */}
              <div className="p-3 rounded-xl bg-[#F8FAFC] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] space-y-1.5">
                <div className="flex items-center gap-2 font-bold text-xs text-[#0F1B2D] dark:text-[#E8EDF5]">
                  <span className="w-5 h-5 rounded-full bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300 flex items-center justify-center text-[10px]">1</span>
                  <span>If iPhone shows &ldquo;404 Not Found&rdquo;:</span>
                </div>
                <p className="text-[11px] text-[#46566C] dark:text-[#A9B6C9] pl-7 leading-relaxed">
                  The Shared Public URL is only live after you click the <strong>&ldquo;Share&rdquo;</strong> button in the top-right header of Google AI Studio. Make sure to click <strong>Share &rarr; Public / Anyone with link</strong> so Google activates the preview link.
                </p>
              </div>

              {/* Reason 2: WhatsApp in-app browser */}
              <div className="p-3 rounded-xl bg-[#F8FAFC] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] space-y-1.5">
                <div className="flex items-center gap-2 font-bold text-xs text-[#0F1B2D] dark:text-[#E8EDF5]">
                  <span className="w-5 h-5 rounded-full bg-[#0E7C86]/20 text-[#0E7C86] flex items-center justify-center text-[10px]">2</span>
                  <span>If sent via WhatsApp / iMessage (Blank or stuck screen):</span>
                </div>
                <p className="text-[11px] text-[#46566C] dark:text-[#A9B6C9] pl-7 leading-relaxed">
                  WhatsApp on iPhone opens links in an embedded mini-browser that blocks cookies and app installs.
                  <br />
                  <strong className="text-[#0F1B2D] dark:text-[#E8EDF5]">The Fix:</strong> On the iPhone inside WhatsApp, look at the bottom-right corner and tap the <strong>Compass / Safari icon</strong> (<Compass className="inline w-3 h-3 text-sky-600" />) or tap the 3 dots &rarr; <strong>&ldquo;Open in Safari&rdquo;</strong>.
                </p>
              </div>

              {/* Reason 3: Dev Link requires Google Login */}
              <div className="p-3 rounded-xl bg-[#F8FAFC] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] space-y-1.5">
                <div className="flex items-center gap-2 font-bold text-xs text-[#0F1B2D] dark:text-[#E8EDF5]">
                  <span className="w-5 h-5 rounded-full bg-[#0E7C86]/20 text-[#0E7C86] flex items-center justify-center text-[10px]">3</span>
                  <span>If testing the Dev Link on iPhone:</span>
                </div>
                <p className="text-[11px] text-[#46566C] dark:text-[#A9B6C9] pl-7 leading-relaxed">
                  The Development URL is strictly private to your Google account (<code>canaraaiclass@gmail.com</code>). In iPhone Safari, you must be signed in with that exact Google account. A trial recipient will receive a 403 Forbidden on the dev link—they must use the <strong>Public Shared Link</strong>.
                </p>
              </div>

              {/* Reason 4: Safari Cookie Settings */}
              <div className="p-3 rounded-xl bg-[#F8FAFC] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] space-y-1.5">
                <div className="flex items-center gap-2 font-bold text-xs text-[#0F1B2D] dark:text-[#E8EDF5]">
                  <span className="w-5 h-5 rounded-full bg-[#0E7C86]/20 text-[#0E7C86] flex items-center justify-center text-[10px]">4</span>
                  <span>iPhone Safari Settings:</span>
                </div>
                <p className="text-[11px] text-[#46566C] dark:text-[#A9B6C9] pl-7 leading-relaxed">
                  On the iPhone, open <strong>Settings &rarr; Safari</strong>:
                  <br />
                  &bull; Ensure <strong>Private Browsing</strong> is not blocking local storage.
                  <br />
                  &bull; Under Advanced, ensure <strong>Block All Cookies</strong> is turned OFF.
                </p>
              </div>

              {/* How to add to home screen */}
              <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/50 space-y-1.5 text-emerald-900 dark:text-emerald-200">
                <strong className="text-xs block font-bold">
                  How to Install on iPhone Once Open in Safari:
                </strong>
                <ol className="list-decimal list-inside space-y-1 text-[11px] text-emerald-950/80 dark:text-emerald-200/80">
                  <li>In Safari, tap the <strong>Share</strong> button (box with upward arrow at bottom).</li>
                  <li>Scroll down and tap <strong>&ldquo;Add to Home Screen&rdquo;</strong>.</li>
                  <li>Tap <strong>&ldquo;Add&rdquo;</strong> in the top right. Paisa Pal will launch as a full-screen app!</li>
                </ol>
              </div>
            </div>
          )}

          {activeTab === 'qr' && (
            <div className="space-y-3 text-center">
              <div className="p-4 bg-white dark:bg-[#0A1626] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl flex flex-col items-center justify-center">
                {qrCodeUrl ? (
                  <img
                    src={qrCodeUrl}
                    alt="Scan to open Paisa Pal on phone"
                    className="w-48 h-48 rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-2 shadow-xs"
                  />
                ) : (
                  <div className="w-48 h-48 rounded-xl bg-slate-100 flex items-center justify-center text-slate-400">
                    <QrCode className="w-12 h-12" />
                  </div>
                )}
                <div className="mt-3 text-xs">
                  <strong className="block text-[#0F1B2D] dark:text-[#E8EDF5] text-sm font-bold">
                    Scan with iPhone or Android Camera
                  </strong>
                  <p className="text-[#6F7E92] dark:text-[#8594AA] text-xs mt-1 max-w-xs mx-auto">
                    Open your iPhone Camera app and point it here. Tap the yellow Safari notification to open Paisa Pal immediately!
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-left">
                <div className="p-2.5 rounded-xl bg-[#F8FAFC] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A]">
                  <div className="flex items-center gap-1.5 font-semibold text-[#0F1B2D] dark:text-[#E8EDF5]">
                    <Smartphone className="w-3.5 h-3.5 text-[#0E7C86]" />
                    <span>Apple iPhone</span>
                  </div>
                  <p className="text-[11px] text-[#6F7E92] dark:text-[#8594AA] mt-1">
                    Opens directly in Safari. Tap Share (square with up arrow) &rarr; &ldquo;Add to Home Screen&rdquo;.
                  </p>
                </div>

                <div className="p-2.5 rounded-xl bg-[#F8FAFC] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A]">
                  <div className="flex items-center gap-1.5 font-semibold text-[#0F1B2D] dark:text-[#E8EDF5]">
                    <Smartphone className="w-3.5 h-3.5 text-[#0E7C86]" />
                    <span>Android Phone</span>
                  </div>
                  <p className="text-[11px] text-[#6F7E92] dark:text-[#8594AA] mt-1">
                    Opens in Chrome. Tap 3 dots (⋮) &rarr; &ldquo;Add to Home screen&rdquo; or &ldquo;Install app&rdquo;.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'guide' && (
            <div className="space-y-3">
              <div className="bg-[#F8FAFC] dark:bg-[#0B1220] p-3.5 rounded-xl border border-[#DCE2EA] dark:border-[#25324A] space-y-2">
                <strong className="text-xs text-[#0F1B2D] dark:text-[#E8EDF5] block font-bold">
                  What makes this trial so easy for anyone?
                </strong>
                <ul className="space-y-2 text-[#46566C] dark:text-[#A9B6C9] leading-relaxed">
                  <li className="flex items-start gap-2">
                    <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 flex-shrink-0" />
                    <span>
                      <strong>Zero login or passwords required:</strong> The recipient does not need to create an account or give an email address. The app opens immediately.
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 flex-shrink-0" />
                    <span>
                      <strong>100% Private local database:</strong> Any trial entries they type or test stay exclusively on their own browser. Nothing is sent to external servers.
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 flex-shrink-0" />
                    <span>
                      <strong>1-Click Sample Data:</strong> A prominent button allows them to populate the app with realistic FDs, SIPs, life insurance, and car insurance to test calculation views and calendar alarms.
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 flex-shrink-0" />
                    <span>
                      <strong>No app store download needed:</strong> They can run it directly in Chrome, Edge, Safari, or install it as an offline home screen app.
                    </span>
                  </li>
                </ul>
              </div>

              <div className="bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/50 p-3 rounded-xl flex items-center gap-2.5 text-emerald-900 dark:text-emerald-200">
                <ShieldCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                <p className="text-[11px] leading-relaxed">
                  Your own data remains safe on your device. The trial recipient receives a clean, independent sandbox that will not overwrite or alter your personal data.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-4 pt-3 border-t border-[#DCE2EA] dark:border-[#25324A] flex items-center justify-between gap-2">
          <div className="text-[11px] text-[#6F7E92] dark:text-[#8594AA] truncate">
            Target: <span className="font-mono text-[#0F1B2D] dark:text-[#E8EDF5]">{urlType === 'shared' ? 'Public Shared (ais-pre)' : 'Dev Link (ais-dev)'}</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-[#0F1B2D] dark:text-[#E8EDF5] font-semibold text-xs transition"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
