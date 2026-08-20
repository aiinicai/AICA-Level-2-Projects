import React, { useState, useRef } from 'react';
import {
  X,
  Sparkles,
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Image as ImageIcon
} from 'lucide-react';
import { Voucher } from '../../types';

interface AIInvoiceScanModalProps {
  isOpen: boolean;
  onClose: () => void;
  onInvoiceParsed: (parsedData: Partial<Voucher>) => void;
}

export const AIInvoiceScanModal: React.FC<AIInvoiceScanModalProps> = ({
  isOpen,
  onClose,
  onInvoiceParsed,
}) => {
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [rawText, setRawText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      setImageBase64(evt.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleRunOCR = async () => {
    if (!imageBase64 && !rawText.trim()) {
      setError('Please upload an invoice receipt image or paste raw invoice text.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const resp = await fetch('/api/intelligence/parse-invoice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          imageBase64: imageBase64 || undefined,
          rawText: rawText || undefined,
        }),
      });

      const data = await resp.json();
      if (!resp.ok || !data.success) {
        throw new Error(data.error || 'Failed to parse invoice with Gemini.');
      }

      onInvoiceParsed(data.parsed);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Error communicating with AI parser service.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-lg w-full overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            <h3 className="font-semibold text-sm">AI Invoice & Receipt OCR Scanner</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4 text-xs">
          <p className="text-slate-600">
            Upload an image of a physical supplier receipt, commercial invoice, or paste text to automatically extract client name, TIN, and line items via <strong>Gemini OCR</strong>.
          </p>

          {/* Upload Area */}
          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-slate-300 hover:border-indigo-500 rounded-lg p-6 flex flex-col items-center justify-center text-center cursor-pointer bg-slate-50/60 transition"
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept="image/*"
              className="hidden"
            />
            {imageBase64 ? (
              <div className="space-y-2">
                <img
                  src={imageBase64}
                  alt="Uploaded preview"
                  className="max-h-32 rounded object-contain border border-slate-200 mx-auto"
                />
                <span className="text-[11px] text-indigo-600 font-medium block">Click to replace image</span>
              </div>
            ) : (
              <>
                <Upload className="w-7 h-7 text-indigo-500 mb-2" />
                <p className="font-semibold text-slate-700">Click or drag & drop invoice photo</p>
                <p className="text-[11px] text-slate-400 mt-0.5">PNG, JPG, WEBP</p>
              </>
            )}
          </div>

          <div className="relative flex py-1 items-center">
            <div className="flex-grow border-t border-slate-200"></div>
            <span className="flex-shrink mx-2 text-[10px] text-slate-400 uppercase font-semibold">Or paste raw text</span>
            <div className="flex-grow border-t border-slate-200"></div>
          </div>

          <div>
            <textarea
              rows={3}
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="e.g. Invoice from Serengeti Logistics Ltd, TIN: 102-491-884, 50 drums Bitumen @ 850,000 TZS..."
              className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-indigo-500/20 text-slate-800 text-xs"
            />
          </div>

          {error && (
            <div className="p-3 bg-rose-50 text-rose-800 border border-rose-200 rounded-md flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Footer Actions */}
          <div className="pt-2 flex items-center justify-end space-x-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 border border-slate-300 text-slate-700 hover:bg-slate-50 rounded font-semibold"
            >
              Cancel
            </button>
            <button
              onClick={handleRunOCR}
              disabled={loading}
              className="flex items-center space-x-1.5 px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded font-semibold shadow-xs transition disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Extracting Data...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Parse & Auto-Fill</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
