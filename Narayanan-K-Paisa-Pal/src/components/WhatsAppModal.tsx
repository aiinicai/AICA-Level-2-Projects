import React, { useState } from 'react';
import { X, Send, Copy, Check, MessageSquare } from 'lucide-react';

interface Props {
  isOpen: boolean;
  whatsappNumber: string;
  digestText: string;
  onSaveNumber: (num: string) => void;
  onClose: () => void;
}

export const WhatsAppModal: React.FC<Props> = ({
  isOpen,
  whatsappNumber,
  digestText,
  onSaveNumber,
  onClose,
}) => {
  const [copied, setCopied] = useState(false);
  const [numInput, setNumInput] = useState(whatsappNumber || '');

  if (!isOpen) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(digestText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleSend = () => {
    const cleanNum = numInput.replace(/\D/g, '');
    if (cleanNum !== whatsappNumber) {
      onSaveNumber(cleanNum);
    }
    const url = `https://wa.me/${cleanNum}?text=${encodeURIComponent(digestText)}`;
    window.open(url, '_blank', 'noopener,noreferrer');
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto"
    >
      <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl max-w-lg w-full p-6 shadow-2xl relative text-[#0F1B2D] dark:text-[#E8EDF5]">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
          aria-label="Close dialog"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 dark:bg-emerald-950/70 dark:text-emerald-300 flex items-center justify-center font-bold">
            <MessageSquare className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-semibold text-lg leading-tight">Send WhatsApp Digest</h3>
            <p className="text-xs text-[#6F7E92] dark:text-[#8594AA]">
              Send upcoming dues and alerts directly to your phone
            </p>
          </div>
        </div>

        <div className="space-y-4 text-sm">
          <div>
            <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
              Your WhatsApp number (with country code, digits only e.g. 919876543210):
            </label>
            <input
              type="tel"
              value={numInput}
              onChange={(e) => setNumInput(e.target.value)}
              placeholder="e.g. 919876543210"
              className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
              Preview formatted message:
            </label>
            <div className="bg-[#EEF1F5] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl p-3 text-xs whitespace-pre-wrap font-mono text-[#0F1B2D] dark:text-[#E8EDF5] max-h-48 overflow-y-auto">
              {digestText}
            </div>
          </div>

          <div className="flex items-center justify-between gap-2 pt-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] hover:bg-slate-50 dark:hover:bg-slate-800 transition"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 text-slate-500" />
                  <span>Copy text</span>
                </>
              )}
            </button>

            <button
              onClick={handleSend}
              disabled={!numInput.trim()}
              className="flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white transition shadow-sm"
            >
              <Send className="w-4 h-4" />
              <span>Open in WhatsApp</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
