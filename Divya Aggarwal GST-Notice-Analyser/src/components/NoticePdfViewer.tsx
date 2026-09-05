import React, { useState } from 'react';
import { ZoomIn, ZoomOut, FileText, Copy, Check } from 'lucide-react';

interface NoticePdfViewerProps {
  pdfDataUrl?: string;
  pdfFileName?: string;
  rawText?: string;
  noticeNumber: string;
  formType: string;
}

export const NoticePdfViewer: React.FC<NoticePdfViewerProps> = ({
  pdfDataUrl,
  pdfFileName,
  rawText,
  noticeNumber,
  formType,
}) => {
  const [zoom, setZoom] = useState(100);
  const [copied, setCopied] = useState(false);
  const [viewMode, setViewMode] = useState<'text' | 'pdf'>(pdfDataUrl ? 'pdf' : 'text');

  const handleCopyText = () => {
    if (rawText) {
      navigator.clipboard.writeText(rawText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white border border-gray-200 rounded-xl overflow-hidden shadow-xs">
      <div className="bg-[#F9FAFB] border-b border-gray-200 px-3 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-indigo-700" />
          <span className="text-xs font-bold text-gray-800">
            {pdfFileName || `${formType} - ${noticeNumber}`}
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 font-bold border border-indigo-200">
            {formType}
          </span>
        </div>

        <div className="flex items-center gap-1">
          {pdfDataUrl && (
            <div className="flex items-center bg-gray-200 rounded-lg p-0.5 mr-2">
              <button
                onClick={() => setViewMode('pdf')}
                className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                  viewMode === 'pdf' ? 'bg-white text-gray-900 shadow-2xs' : 'text-gray-600'
                }`}
              >
                PDF View
              </button>
              <button
                onClick={() => setViewMode('text')}
                className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                  viewMode === 'text' ? 'bg-white text-gray-900 shadow-2xs' : 'text-gray-600'
                }`}
              >
                Extracted Text
              </button>
            </div>
          )}

          <div className="flex items-center gap-1 border-r border-gray-200 pr-2 mr-1">
            <button
              onClick={() => setZoom((z) => Math.max(70, z - 10))}
              className="p-1 hover:bg-gray-200 rounded text-gray-600 cursor-pointer"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="text-[10px] font-mono font-semibold text-gray-600 min-w-8 text-center">
              {zoom}%
            </span>
            <button
              onClick={() => setZoom((z) => Math.min(150, z + 10))}
              className="p-1 hover:bg-gray-200 rounded text-gray-600 cursor-pointer"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>

          <button
            onClick={handleCopyText}
            className="flex items-center gap-1 px-2 py-1 hover:bg-gray-200 rounded text-[11px] font-medium text-gray-700 cursor-pointer"
            title="Copy Notice Text"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4 bg-[#F3F4F6]">
        {viewMode === 'pdf' && pdfDataUrl ? (
          <div className="h-full w-full flex justify-center">
            <iframe
              src={`${pdfDataUrl}#zoom=${zoom}`}
              title="Notice PDF Viewer"
              className="w-full h-full rounded border border-gray-300 shadow-xs bg-white"
            />
          </div>
        ) : (
          <div
            className="bg-white rounded-lg p-6 shadow-sm border border-gray-200 min-h-full font-mono text-xs leading-relaxed text-gray-800 whitespace-pre-wrap select-text max-w-3xl mx-auto"
            style={{ fontSize: `${(zoom / 100) * 11}px` }}
          >
            <div className="border-b border-gray-200 pb-3 mb-4 text-center font-sans">
              <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                Original Scanned Notice Transcription
              </div>
              <div className="text-sm font-bold text-gray-900 mt-0.5">
                FORM GST {formType}
              </div>
              <div className="text-[11px] text-gray-600">
                Notice Ref: {noticeNumber}
              </div>
            </div>

            {rawText || 'No raw notice text extracted yet.'}
          </div>
        )}
      </div>
    </div>
  );
};
