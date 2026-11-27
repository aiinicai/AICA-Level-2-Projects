import React, { useEffect, useState } from 'react';
import QRCode from 'qrcode';
import {
  X,
  QrCode,
  Copy,
  Check,
  ExternalLink,
  Smartphone,
  AlertCircle,
  HelpCircle,
  Share2,
  Download,
  Send
} from 'lucide-react';

interface MobileQRCodeModalProps {
  onClose: () => void;
}

export const MobileQRCodeModal: React.FC<MobileQRCodeModalProps> = ({ onClose }) => {
  const [devQrUrl, setDevQrUrl] = useState('');
  const [publishedQrUrl, setPublishedQrUrl] = useState('');
  const [copiedLink, setCopiedLink] = useState<string | null>(null);

  // Exact clean AI Studio Published and Dev URLs
  const publishedUrl = 'https://ais-pre-vjcjzsbq6gh5mvl3nxprfp-969974775552.europe-west2.run.app';
  const devUrl = 'https://ais-dev-vjcjzsbq6gh5mvl3nxprfp-969974775552.europe-west2.run.app';

  // Default to AI Studio Published URL
  const [selectedUrlType, setSelectedUrlType] = useState<'published' | 'dev'>('published');

  const currentUrl = selectedUrlType === 'published' ? publishedUrl : devUrl;

  useEffect(() => {
    // Generate QR code for the Published URL (primary)
    QRCode.toDataURL(publishedUrl, {
      width: 280,
      margin: 1.5,
      color: {
        dark: '#090d16',
        light: '#ffffff'
      }
    }).then(setPublishedQrUrl).catch(console.error);

    // Generate QR code for Dev URL
    QRCode.toDataURL(devUrl, {
      width: 280,
      margin: 1.5,
      color: {
        dark: '#090d16',
        light: '#ffffff'
      }
    }).then(setDevQrUrl).catch(console.error);
  }, [publishedUrl, devUrl]);

  const handleCopy = (url: string, id: string) => {
    navigator.clipboard.writeText(url);
    setCopiedLink(id);
    setTimeout(() => setCopiedLink(null), 2500);
  };

  const handleShare = async () => {
    if (typeof navigator !== 'undefined' && navigator.share) {
      try {
        await navigator.share({
          title: 'DirhamTrack - Published App on Android Phone',
          text: 'Open DirhamTrack published app on your Android phone to track UAE finances and auto-record bank alerts:',
          url: currentUrl
        });
      } catch (err) {
        handleCopy(currentUrl, 'share');
      }
    } else {
      handleCopy(currentUrl, 'share');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto animate-fade-in">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl my-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-teal-500/20 text-teal-400 border border-teal-500/30 flex items-center justify-center shrink-0">
              <Smartphone className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                Download on Android Phone
              </h3>
              <p className="text-xs text-slate-400">Scan published QR code or open link directly on mobile</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Android Quick Instructions Banner */}
        <div className="p-3.5 bg-gradient-to-r from-teal-950/50 to-slate-950 border border-teal-500/30 rounded-2xl mb-4 text-xs space-y-2">
          <div className="flex items-center gap-2 text-white font-bold">
            <Download className="w-4 h-4 text-teal-400" />
            <span>How to Install Published App on Android Phone:</span>
          </div>
          <div className="space-y-1.5 text-slate-300 text-[11px] leading-relaxed">
            <p>
              <strong>• Using Android Browser / Chrome:</strong> Open the published link &rarr; Tap the 3 dots in the top right (<code className="text-teal-300 bg-slate-900 px-1 py-0.5 rounded">⋮</code>) &rarr; Tap <strong>"Install app"</strong> or <strong>"Add to Home screen"</strong>.
            </p>
            <p>
              <strong>• Using In-App Install Prompt:</strong> Look for the <strong>"Install PWA"</strong> button in the top navigation bar to add DirhamTrack directly to your home screen with offline support.
            </p>
          </div>
        </div>

        {/* URL Type Switcher */}
        <div className="grid grid-cols-2 gap-1.5 p-1 bg-slate-950 rounded-xl mb-4 text-xs font-semibold">
          <button
            type="button"
            onClick={() => setSelectedUrlType('published')}
            className={`py-2 px-3 rounded-lg transition cursor-pointer flex items-center justify-center gap-1.5 ${
              selectedUrlType === 'published'
                ? 'bg-teal-500 text-slate-950 font-bold shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-slate-950" />
            <span>AI Studio Published Link</span>
          </button>
          <button
            type="button"
            onClick={() => setSelectedUrlType('dev')}
            className={`py-2 px-3 rounded-lg transition cursor-pointer ${
              selectedUrlType === 'dev'
                ? 'bg-teal-500 text-slate-950 font-bold shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Dev Preview Link
          </button>
        </div>

        {/* QR Code Display */}
        <div className="flex flex-col items-center bg-slate-950 p-5 rounded-2xl border border-slate-800 mb-4">
          <div className="p-3 bg-white rounded-2xl shadow-lg mb-3">
            {selectedUrlType === 'published' && publishedQrUrl ? (
              <img src={publishedQrUrl} alt="DirhamTrack Published QR Code" className="w-52 h-52" />
            ) : devQrUrl ? (
              <img src={devQrUrl} alt="DirhamTrack Dev Preview QR Code" className="w-52 h-52" />
            ) : (
              <div className="w-52 h-52 flex items-center justify-center text-slate-500">
                Generating QR...
              </div>
            )}
          </div>
          <p className="text-xs text-slate-300 font-medium">
            Open camera on your Android phone to scan and launch
          </p>
        </div>

        {/* Clean Copy Link Box */}
        <div className="space-y-2 mb-4">
          <label className="block text-[11px] text-slate-400 font-semibold">
            {selectedUrlType === 'published' ? 'AI Studio Published Link for Android:' : 'Development Preview Link for Android:'}
          </label>
          <div className="flex items-center gap-2 bg-slate-950 border border-slate-700 rounded-xl p-2">
            <input
              type="text"
              readOnly
              value={currentUrl}
              className="bg-transparent flex-1 text-xs text-teal-300 font-mono outline-none px-2 select-all"
            />
            <button
              onClick={() => handleCopy(currentUrl, selectedUrlType)}
              className="px-3 py-1.5 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-lg flex items-center gap-1.5 transition whitespace-nowrap cursor-pointer shadow"
            >
              {copiedLink === selectedUrlType ? (
                <>
                  <Check className="w-3.5 h-3.5" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy Link</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={handleShare}
            className="flex-1 py-2.5 px-3 bg-slate-800 hover:bg-slate-750 text-teal-300 text-xs font-semibold rounded-xl border border-slate-700 flex items-center justify-center gap-2 transition cursor-pointer"
          >
            <Share2 className="w-4 h-4" />
            <span>Share Link to Android Phone</span>
          </button>
          <a
            href={currentUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 py-2.5 px-3 bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold rounded-xl flex items-center justify-center gap-2 transition shadow cursor-pointer text-center"
          >
            <ExternalLink className="w-4 h-4" />
            <span>Open in Browser</span>
          </a>
        </div>
      </div>
    </div>
  );
};
