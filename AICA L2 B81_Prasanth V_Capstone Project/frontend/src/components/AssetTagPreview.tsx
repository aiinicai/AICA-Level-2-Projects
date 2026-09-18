import React, { useEffect, useRef, useState } from 'react';
import bwipjs from 'bwip-js';
import { Download, FileText, Printer, FileSpreadsheet, Eye, X } from 'lucide-react';
import api from '../services/api';

interface AssetTagPreviewProps {
  companyName: string;
  logoUrl?: string;
  assetId: string;
  sapNumber?: string;
  description?: string;
  location?: string;
  codeType: 'BARCODE' | 'QR_CODE';
  widthMm?: number;
  heightMm?: number;
  showActions?: boolean;
  scale?: number;
  id?: number; // DB asset ID if already saved
}

export const AssetTagPreview: React.FC<AssetTagPreviewProps> = ({
  companyName = 'REFERENCE COMPANY NAME',
  logoUrl,
  assetId = 'FA-000001',
  sapNumber = '36007672-0',
  description = 'WEIG-MCHN',
  location = 'MCP',
  codeType = 'BARCODE',
  widthMm = 70,
  heightMm = 35,
  showActions = true,
  scale = 1.0,
  id,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [showPdfModal, setShowPdfModal] = useState(false);
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState<string | null>(null);
  const [loadingPdf, setLoadingPdf] = useState(false);

  const handleLivePdfPreview = async () => {
    try {
      setLoadingPdf(true);
      if (id) {
        setPdfPreviewUrl(`/api/assets/${id}/pdf#toolbar=1`);
      } else {
        const res = await api.post(
          '/assets/preview-pdf',
          {
            asset_id: assetId,
            company_name: companyName,
            sap_number: sapNumber,
            description: description,
            location: location,
            code_type: codeType,
            width_mm: widthMm,
            height_mm: heightMm,
          },
          { responseType: 'blob' }
        );
        const blobUrl = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
        setPdfPreviewUrl(blobUrl);
      }
      setShowPdfModal(true);
    } catch (e) {
      console.error('Failed to generate PDF preview:', e);
    } finally {
      setLoadingPdf(false);
    }
  };

  // Millimeters to pixels scale factor (1 mm ≈ 4.8 px for crisp screen preview, 11.8 px for 300 DPI print)
  const pxPerMm = 5.2 * scale;
  const tagWidthPx = Math.round(widthMm * pxPerMm);
  const tagHeightPx = Math.round(heightMm * pxPerMm);

  useEffect(() => {
    if (!canvasRef.current || !assetId) return;

    try {
      if (codeType === 'QR_CODE') {
        bwipjs.toCanvas(canvasRef.current, {
          bcid: 'qrcode',
          text: assetId,
          scale: 3,
          eclevel: 'M',
          includetext: false,
        });
      } else {
        bwipjs.toCanvas(canvasRef.current, {
          bcid: 'code128',
          text: assetId,
          scale: 2,
          height: 10,
          includetext: false, // We render the human-readable text cleanly below
          textxalign: 'center',
        });
      }
    } catch (e) {
      console.warn('Barcode generation canvas error:', e);
    }
  }, [assetId, codeType, widthMm, heightMm, scale]);

  const handleDownloadPng = async () => {
    if (id) {
      // Backend high-res render endpoint
      window.open(`/api/assets/${id}/image`, '_blank');
    } else {
      // Client-side canvas export fallback
      const link = document.createElement('a');
      link.download = `${assetId || 'asset_tag'}.png`;
      if (canvasRef.current) {
        link.href = canvasRef.current.toDataURL('image/png');
        link.click();
      }
    }
  };

  const handleDownloadPdf = async () => {
    if (id) {
      window.open(`/api/assets/${id}/pdf`, '_blank');
    } else {
      try {
        const res = await api.post(
          '/assets/preview-pdf',
          {
            asset_id: assetId,
            company_name: companyName,
            sap_number: sapNumber,
            description: description,
            location: location,
            code_type: codeType,
            width_mm: widthMm,
            height_mm: heightMm,
          },
          { responseType: 'blob' }
        );
        const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
        const link = document.createElement('a');
        link.href = url;
        link.download = `${assetId || 'asset_tag'}.pdf`;
        document.body.appendChild(link);
        link.click();
        link.remove();
      } catch (err) {
        console.error('PDF download error:', err);
      }
    }
  };

  const handleDownloadDocx = async () => {
    if (id) {
      window.open(`/api/assets/${id}/docx`, '_blank');
    } else {
      try {
        const res = await api.post(
          '/assets/preview-docx',
          {
            asset_id: assetId,
            company_name: companyName,
            sap_number: sapNumber,
            description: description,
            location: location,
            code_type: codeType,
            width_mm: widthMm,
            height_mm: heightMm,
          },
          { responseType: 'blob' }
        );
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement('a');
        link.href = url;
        link.download = `${assetId || 'asset_tag'}.docx`;
        document.body.appendChild(link);
        link.click();
        link.remove();
      } catch (err) {
        console.error('DOCX download error:', err);
      }
    }
  };

  return (
    <div className="flex flex-col items-center">
      {/* Physical Asset Tag Representation (Faithful replica of Reference Photo) */}
      <div
        id="physical-asset-tag"
        className="bg-white border-2 border-slate-800 rounded-sm shadow-md flex flex-col justify-between overflow-hidden relative select-none"
        style={{
          width: `${tagWidthPx}px`,
          height: `${tagHeightPx}px`,
          padding: '8px 10px',
          boxSizing: 'border-box',
          fontFamily: 'system-ui, -apple-system, sans-serif',
        }}
      >
        {/* Header: Company Name / Logo */}
        <div className="w-full flex items-center justify-center gap-2 pb-1 border-b border-slate-300">
          {logoUrl ? (
            <img src={logoUrl} alt="Logo" className="h-4 object-contain max-w-[40px]" />
          ) : null}
          <div
            className="font-bold text-slate-900 tracking-tight leading-none text-center truncate uppercase"
            style={{ fontSize: `${Math.max(8.5, 10.5 * scale)}px` }}
          >
            {companyName || 'COMPANY NAME'}
          </div>
        </div>

        {codeType === 'BARCODE' ? (
          /* Reference Barcode Layout: Key-values top, Barcode bottom */
          <div className="flex-1 flex flex-col justify-between py-1">
            {/* Key-Value Details */}
            <div className="grid grid-cols-[80px_1fr] gap-x-1 gap-y-0.5 text-slate-900 leading-tight">
              <span className="font-bold text-slate-800 uppercase" style={{ fontSize: `${Math.max(7.5, 9 * scale)}px` }}>
                SAP NO
              </span>
              <span className="font-semibold" style={{ fontSize: `${Math.max(7.5, 9 * scale)}px` }}>
                : {sapNumber || '—'}
              </span>

              <span className="font-bold text-slate-800 uppercase" style={{ fontSize: `${Math.max(7.5, 9 * scale)}px` }}>
                DESCRIPTION
              </span>
              <span className="font-semibold truncate" style={{ fontSize: `${Math.max(7.5, 9 * scale)}px` }}>
                : {description || '—'}
              </span>

              <span className="font-bold text-slate-800 uppercase" style={{ fontSize: `${Math.max(7.5, 9 * scale)}px` }}>
                LOCATION
              </span>
              <span className="font-semibold truncate" style={{ fontSize: `${Math.max(7.5, 9 * scale)}px` }}>
                : {location || '—'}
              </span>
            </div>

            {/* Bottom Barcode Section */}
            <div className="pt-1 border-t border-slate-200 flex flex-col items-center">
              <canvas ref={canvasRef} className="max-w-full h-8 object-contain" />
              <div
                className="font-bold tracking-widest text-slate-900 text-center uppercase"
                style={{ fontSize: `${Math.max(8, 9.5 * scale)}px`, marginTop: '1px' }}
              >
                {assetId || 'FA-000000'}
              </div>
            </div>
          </div>
        ) : (
          /* QR Code Layout: Key-values left, QR code right */
          <div className="flex-1 flex items-center justify-between py-1 gap-2">
            <div className="flex-1 flex flex-col justify-center gap-1 text-slate-900 leading-tight">
              <div className="grid grid-cols-[65px_1fr] gap-x-1 gap-y-0.5">
                <span className="font-bold text-slate-800 uppercase" style={{ fontSize: `${Math.max(7.5, 8.5 * scale)}px` }}>
                  SAP NO
                </span>
                <span className="font-semibold" style={{ fontSize: `${Math.max(7.5, 8.5 * scale)}px` }}>
                  : {sapNumber || '—'}
                </span>

                <span className="font-bold text-slate-800 uppercase" style={{ fontSize: `${Math.max(7.5, 8.5 * scale)}px` }}>
                  DESC
                </span>
                <span className="font-semibold truncate" style={{ fontSize: `${Math.max(7.5, 8.5 * scale)}px` }}>
                  : {description || '—'}
                </span>

                <span className="font-bold text-slate-800 uppercase" style={{ fontSize: `${Math.max(7.5, 8.5 * scale)}px` }}>
                  LOC
                </span>
                <span className="font-semibold truncate" style={{ fontSize: `${Math.max(7.5, 8.5 * scale)}px` }}>
                  : {location || '—'}
                </span>
              </div>

              <div className="mt-1 pt-1 border-t border-slate-200">
                <span className="font-bold text-slate-900" style={{ fontSize: `${Math.max(8, 9.5 * scale)}px` }}>
                  ID: {assetId || 'FA-000000'}
                </span>
              </div>
            </div>

            {/* QR Canvas */}
            <div className="w-18 h-18 flex items-center justify-center p-0.5 border border-slate-200 rounded">
              <canvas ref={canvasRef} className="w-16 h-16 object-contain" />
            </div>
          </div>
        )}
      </div>

      {/* Dimensions & Quality Indicator */}
      <div className="mt-2 text-xs text-slate-500 font-medium flex items-center gap-2">
        <span>Dimension: {widthMm} × {heightMm} mm</span>
        <span>•</span>
        <span>Format: {codeType === 'BARCODE' ? 'Code 128' : 'QR Code'}</span>
      </div>

      {/* Action Buttons */}
      {showActions && (
        <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
          <button
            type="button"
            onClick={handleLivePdfPreview}
            disabled={loadingPdf}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 shadow-sm transition"
            title="Open Live PDF Preview"
          >
            <Eye className="w-3.5 h-3.5 text-blue-600" />
            {loadingPdf ? 'Loading PDF...' : 'Live PDF Preview'}
          </button>

          <button
            type="button"
            onClick={handleDownloadPng}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 shadow-sm transition"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            Download PNG
          </button>

          <button
            type="button"
            onClick={handleDownloadPdf}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 shadow-sm transition"
          >
            <FileText className="w-3.5 h-3.5 text-red-500" />
            Download PDF
          </button>

          <button
            type="button"
            onClick={handleDownloadDocx}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 shadow-sm transition"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-blue-600" />
            Word (.docx)
          </button>
        </div>
      )}

      {/* Live PDF Preview Modal */}
      {showPdfModal && pdfPreviewUrl && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="bg-white rounded-2xl border border-slate-200 w-full max-w-3xl h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="px-5 py-3.5 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-red-400" />
                <span className="text-xs font-bold uppercase tracking-wide">
                  Live PDF Tag Preview — {assetId}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleDownloadPdf}
                  className="px-2.5 py-1 bg-red-600 hover:bg-red-500 text-white rounded text-xs font-bold transition flex items-center gap-1"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download PDF
                </button>
                <button
                  type="button"
                  onClick={handleDownloadDocx}
                  className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-bold transition flex items-center gap-1"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  Download Word
                </button>
                <button
                  type="button"
                  onClick={() => setShowPdfModal(false)}
                  className="p-1 hover:bg-slate-800 text-slate-400 hover:text-white rounded-md transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
            <div className="flex-1 bg-slate-100 p-2">
              <iframe
                src={pdfPreviewUrl}
                title="Live PDF Preview"
                className="w-full h-full rounded-lg border border-slate-300 shadow-inner bg-white"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
