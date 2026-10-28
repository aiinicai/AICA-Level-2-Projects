import React, { useState } from 'react';
import {
  X,
  Download,
  Paperclip,
  ZoomIn,
  ZoomOut,
  RotateCw,
  ExternalLink,
  FileText,
} from 'lucide-react';
import { AttachmentRecord } from '../utils/attachmentStorage';

interface Props {
  attachment: AttachmentRecord | null;
  itemName: string;
  onClose: () => void;
}

export const AttachmentViewerModal: React.FC<Props> = ({
  attachment,
  itemName,
  onClose,
}) => {
  const [scale, setScale] = useState<number>(1);
  const [rotation, setRotation] = useState<number>(0);

  if (!attachment) return null;

  const isImage =
    attachment.type.startsWith('image/') ||
    /\.(jpe?g|png|webp|gif|bmp)$/i.test(attachment.name);

  // Direct image source: previewUrl if provided, or dataUrl if it is an image
  const imageSrc =
    attachment.previewUrl || (isImage ? attachment.dataUrl : undefined);

  // Direct link to the actual PDF for downloads or opening in a new tab
  const pdfDownloadUrl = attachment.pdfUrl || attachment.dataUrl;

  const handleDownload = () => {
    const a = document.createElement('a');
    a.href = pdfDownloadUrl;
    a.download = attachment.name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleZoomIn = () => setScale((prev) => Math.min(prev + 0.25, 3));
  const handleZoomOut = () => setScale((prev) => Math.max(prev - 0.25, 0.5));
  const handleResetZoom = () => {
    setScale(1);
    setRotation(0);
  };
  const handleRotate = () => setRotation((prev) => (prev + 90) % 360);

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-2 sm:p-4 overflow-y-auto"
    >
      <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl max-w-4xl w-full max-h-[94vh] flex flex-col shadow-2xl relative text-[#0F1B2D] dark:text-[#E8EDF5] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3.5 border-b border-[#DCE2EA] dark:border-[#25324A] bg-white dark:bg-[#131C2E] z-10">
          <div className="flex items-center gap-2.5 min-w-0 pr-3">
            <div className="p-2 rounded-xl bg-teal-50 dark:bg-teal-950/60 text-[#0E7C86] dark:text-teal-300">
              {attachment.pdfUrl || attachment.name.endsWith('.pdf') ? (
                <FileText className="w-5 h-5" />
              ) : (
                <Paperclip className="w-5 h-5" />
              )}
            </div>
            <div className="truncate">
              <h3 className="font-semibold text-sm sm:text-base truncate">
                {attachment.name}
              </h3>
              <p className="text-[11px] sm:text-xs text-[#6F7E92] dark:text-[#8594AA] truncate">
                Attached to <span className="font-medium">{itemName}</span> ·{' '}
                {(attachment.size / 1024).toFixed(0)} KB
              </p>
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="flex items-center gap-1.5 sm:gap-2">
            {/* Zoom & Rotate Controls */}
            {imageSrc && (
              <div className="hidden sm:flex items-center bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5 border border-slate-200 dark:border-slate-700 mr-1">
                <button
                  type="button"
                  onClick={handleZoomOut}
                  disabled={scale <= 0.5}
                  className="p-1.5 rounded-md hover:bg-white dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 disabled:opacity-40 transition"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  onClick={handleResetZoom}
                  className="px-2 py-1 text-[11px] font-mono font-medium hover:bg-white dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-md transition"
                  title="Reset Zoom"
                >
                  {Math.round(scale * 100)}%
                </button>
                <button
                  type="button"
                  onClick={handleZoomIn}
                  disabled={scale >= 3}
                  className="p-1.5 rounded-md hover:bg-white dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 disabled:opacity-40 transition"
                  title="Zoom In"
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  onClick={handleRotate}
                  className="p-1.5 rounded-md hover:bg-white dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition"
                  title="Rotate 90 degrees"
                >
                  <RotateCw className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {attachment.pdfUrl && (
              <a
                href={attachment.pdfUrl}
                target="_blank"
                rel="noreferrer"
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-[#DCE2EA] dark:border-[#25324A] text-xs font-semibold hover:border-[#0E7C86] text-[#0B3B66] dark:text-[#5B9BE0] transition"
                title="Open PDF file in a new tab"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>Open PDF</span>
              </a>
            )}

            <button
              onClick={handleDownload}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#0E7C86] hover:bg-[#128e9a] text-white text-xs font-semibold shadow-xs transition"
              title="Download original document"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download</span>
            </button>

            <button
              onClick={onClose}
              className="p-1.5 rounded-xl text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              aria-label="Close dialog"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-auto p-4 sm:p-6 flex items-center justify-center min-h-[50vh] max-h-[78vh] bg-slate-900/95 relative select-none">
          {imageSrc ? (
            <div className="max-w-full max-h-full overflow-auto flex items-center justify-center p-2">
              <img
                src={imageSrc}
                alt={attachment.name}
                style={{
                  transform: `scale(${scale}) rotate(${rotation}deg)`,
                  transformOrigin: 'center center',
                  transition: 'transform 0.15s ease-out',
                }}
                className="max-w-full max-h-[72vh] object-contain rounded-lg shadow-2xl border border-slate-800 bg-white"
              />
            </div>
          ) : (
            <div className="text-center py-12 px-6 max-w-md space-y-4 bg-white dark:bg-[#131C2E] rounded-2xl shadow-lg border border-[#DCE2EA] dark:border-[#25324A]">
              <div className="w-14 h-14 mx-auto rounded-2xl bg-teal-50 dark:bg-teal-950/60 text-[#0E7C86] flex items-center justify-center">
                <FileText className="w-7 h-7" />
              </div>
              <div>
                <h4 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
                  {attachment.name}
                </h4>
                <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mt-1">
                  PDF document attached to {itemName} (
                  {(attachment.size / 1024).toFixed(0)} KB)
                </p>
              </div>

              <div className="flex items-center justify-center gap-3 pt-2">
                {attachment.pdfUrl && (
                  <a
                    href={attachment.pdfUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-[#DCE2EA] dark:border-[#25324A] text-xs font-semibold text-[#0B3B66] dark:text-[#5B9BE0] hover:bg-slate-50 dark:hover:bg-slate-800 transition"
                  >
                    <ExternalLink className="w-4 h-4" />
                    <span>Open in Browser</span>
                  </a>
                )}
                <button
                  type="button"
                  onClick={handleDownload}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#0E7C86] hover:bg-[#128e9a] text-white text-xs font-semibold shadow-xs transition"
                >
                  <Download className="w-4 h-4" />
                  <span>Download Document</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer info banner */}
        <div className="px-4 sm:px-6 py-2.5 bg-white dark:bg-[#131C2E] border-t border-[#DCE2EA] dark:border-[#25324A] flex flex-wrap items-center justify-between text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
          <div>
            <span>Viewing certificate: </span>
            <strong className="text-[#0F1B2D] dark:text-[#E8EDF5]">{itemName}</strong>
          </div>
          <div className="flex items-center gap-3">
            {imageSrc && <span>Scroll or use +/- to zoom</span>}
            <button
              onClick={handleDownload}
              className="font-medium text-[#0E7C86] hover:underline flex items-center gap-1"
            >
              <Download className="w-3 h-3" />
              <span>Save a copy</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
