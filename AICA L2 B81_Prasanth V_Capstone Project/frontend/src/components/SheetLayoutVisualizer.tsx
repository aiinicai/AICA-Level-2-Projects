import React, { useState, useEffect } from 'react';
import { Grid, Eye, Printer, FileText, ChevronLeft, ChevronRight, X, ZoomIn, ZoomOut, Maximize2, FileSpreadsheet, Layers, Download } from 'lucide-react';
import { AssetTagPreview } from './AssetTagPreview';
import { Asset } from '../types';
import api from '../services/api';

interface SheetLayoutVisualizerProps {
  pageSize: string;
  orientation: 'PORTRAIT' | 'LANDSCAPE';
  columns: number;
  rows: number;
  labelsPerPage: number;
  totalItems: number;
  labelWidthMm: number;
  labelHeightMm: number;
  assets?: Asset[];
  onPrintPdf?: () => void;
  onPrintDocx?: () => void;
}

export const SheetLayoutVisualizer: React.FC<SheetLayoutVisualizerProps> = ({
  pageSize,
  orientation,
  columns,
  rows,
  labelsPerPage,
  totalItems,
  labelWidthMm,
  labelHeightMm,
  assets = [],
  onPrintPdf,
  onPrintDocx,
}) => {
  const isLandscape = orientation === 'LANDSCAPE';
  const totalPages = Math.ceil((assets.length || totalItems) / labelsPerPage) || 1;
  const [currentPage, setCurrentPage] = useState(1);
  const [showFullPreviewModal, setShowFullPreviewModal] = useState(false);
  const [previewTab, setPreviewTab] = useState<'GRID' | 'PDF' | 'DOCX'>('GRID');
  const [zoomLevel, setZoomLevel] = useState(1.0);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [loadingPdf, setLoadingPdf] = useState(false);

  // Load PDF Stream when switching to PDF tab or opening modal
  const loadPdfStream = async () => {
    if (assets.length === 0) return;
    try {
      setLoadingPdf(true);
      const res = await api.post(
        '/printing/generate-sheet-pdf',
        {
          page_size: pageSize,
          orientation: orientation,
          label_width_mm: labelWidthMm,
          label_height_mm: labelHeightMm,
          columns: columns,
          rows: rows,
        },
        {
          params: { asset_ids: assets.map((a) => a.id) },
          responseType: 'blob',
        }
      );
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      setPdfBlobUrl(url);
    } catch (e) {
      console.error('Failed to load PDF stream:', e);
    } finally {
      setLoadingPdf(false);
    }
  };

  useEffect(() => {
    if (showFullPreviewModal && previewTab === 'PDF' && !pdfBlobUrl) {
      loadPdfStream();
    }
  }, [showFullPreviewModal, previewTab]);

  // Slice assets for current preview page
  const pageStartIndex = (currentPage - 1) * labelsPerPage;
  const pageAssets = assets.slice(pageStartIndex, pageStartIndex + labelsPerPage);

  const handleNativePrint = () => {
    window.print();
  };

  return (
    <div className="bg-slate-900 rounded-xl p-5 border border-slate-800 text-white flex flex-col items-center">
      {/* Visualizer Header */}
      <div className="w-full flex items-center justify-between pb-3 mb-4 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Grid className="w-4 h-4 text-blue-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Intelligent Sheet Layout ({pageSize} {orientation})
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowFullPreviewModal(true)}
            className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-[11px] font-bold shadow transition"
          >
            <Eye className="w-3.5 h-3.5" />
            Live Full Preview
          </button>
          <span className="text-xs bg-blue-500/20 text-blue-300 border border-blue-500/30 px-2 py-0.5 rounded font-mono font-semibold">
            {columns} × {rows} = {labelsPerPage} / page
          </span>
        </div>
      </div>

      {/* Interactive Miniature Sheet Canvas */}
      <div
        className={`bg-white rounded-md shadow-2xl p-3 flex flex-col justify-center transition-all overflow-hidden relative ${
          isLandscape ? 'w-[340px] h-[235px]' : 'w-[235px] h-[335px]'
        }`}
      >
        <div
          className="w-full h-full border border-dashed border-slate-300 rounded p-1 grid gap-1"
          style={{
            gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
            gridTemplateRows: `repeat(${rows}, minmax(0, 1fr))`,
          }}
        >
          {Array.from({ length: labelsPerPage }).map((_, idx) => {
            const ast = pageAssets[idx];
            return (
              <div
                key={idx}
                className={`border rounded-xs flex flex-col items-center justify-center p-0.5 text-slate-800 font-semibold truncate transition select-none ${
                  ast
                    ? 'bg-blue-50/50 border-blue-300 shadow-2xs'
                    : 'bg-slate-50 border-dashed border-slate-200 text-slate-300'
                }`}
              >
                {ast ? (
                  <div className="w-full text-center truncate">
                    <div className="text-[6.5px] font-bold text-slate-900 leading-none truncate">
                      {ast.asset_id}
                    </div>
                    <div className="text-[5px] text-slate-500 truncate leading-tight">
                      {ast.description || 'Asset Tag'}
                    </div>
                  </div>
                ) : (
                  <span className="text-[6px] font-mono text-slate-400">Empty Slot</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Metrics Bar */}
      <div className="mt-4 grid grid-cols-3 gap-3 w-full text-center">
        <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700">
          <div className="text-[10px] text-slate-400 font-medium">Tag Dimensions</div>
          <div className="text-xs font-bold text-white font-mono">{labelWidthMm} × {labelHeightMm} mm</div>
        </div>
        <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700">
          <div className="text-[10px] text-slate-400 font-medium">Labels per Sheet</div>
          <div className="text-xs font-bold text-blue-400 font-mono">{labelsPerPage} tags</div>
        </div>
        <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700">
          <div className="text-[10px] text-slate-400 font-medium">Total Sheets</div>
          <div className="text-xs font-bold text-emerald-400 font-mono">{totalPages} pages</div>
        </div>
      </div>

      {/* Full Screen / High Fidelity WYSIWYG Print Preview Modal */}
      {showFullPreviewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 overflow-hidden">
          <div className="bg-slate-900 rounded-2xl border border-slate-800 w-full max-w-5xl h-[92vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95">
            {/* Modal Header */}
            <div className="bg-slate-900 px-6 py-4 border-b border-slate-800 flex items-center justify-between text-white">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-600/20 text-blue-400 border border-blue-500/30 rounded-lg">
                  <Printer className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Interactive Sheet Print Preview</h3>
                  <p className="text-xs text-slate-400 font-mono">
                    {pageSize} {orientation} • {columns} cols × {rows} rows • Page {currentPage} of {totalPages}
                  </p>
                </div>
              </div>

              {/* Preview Format Tabs */}
              <div className="flex items-center gap-1 bg-slate-800 p-1 rounded-lg border border-slate-700">
                <button
                  type="button"
                  onClick={() => setPreviewTab('GRID')}
                  className={`px-2.5 py-1 rounded text-xs font-bold transition flex items-center gap-1.5 ${
                    previewTab === 'GRID'
                      ? 'bg-blue-600 text-white'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <Grid className="w-3.5 h-3.5" />
                  Visual Grid
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setPreviewTab('PDF');
                    if (!pdfBlobUrl) loadPdfStream();
                  }}
                  className={`px-2.5 py-1 rounded text-xs font-bold transition flex items-center gap-1.5 ${
                    previewTab === 'PDF'
                      ? 'bg-red-600 text-white'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  Live PDF Preview
                </button>
                <button
                  type="button"
                  onClick={() => setPreviewTab('DOCX')}
                  className={`px-2.5 py-1 rounded text-xs font-bold transition flex items-center gap-1.5 ${
                    previewTab === 'DOCX'
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  Word (.docx) Preview
                </button>
              </div>

              {/* Controls */}
              <div className="flex items-center gap-2">
                {/* Zoom */}
                {previewTab === 'GRID' && (
                  <div className="flex items-center bg-slate-800 rounded-lg border border-slate-700 px-1 py-0.5">
                    <button
                      onClick={() => setZoomLevel((z) => Math.max(0.6, z - 0.1))}
                      className="p-1 hover:text-blue-400 text-slate-300"
                      title="Zoom Out"
                    >
                      <ZoomOut className="w-4 h-4" />
                    </button>
                    <span className="text-[11px] font-mono px-2 text-slate-300 font-bold">
                      {Math.round(zoomLevel * 100)}%
                    </span>
                    <button
                      onClick={() => setZoomLevel((z) => Math.min(1.6, z + 0.1))}
                      className="p-1 hover:text-blue-400 text-slate-300"
                      title="Zoom In"
                    >
                      <ZoomIn className="w-4 h-4" />
                    </button>
                  </div>
                )}

                {/* Page Navigation */}
                {totalPages > 1 && previewTab === 'GRID' && (
                  <div className="flex items-center bg-slate-800 rounded-lg border border-slate-700 px-1 py-0.5">
                    <button
                      disabled={currentPage <= 1}
                      onClick={() => setCurrentPage((p) => p - 1)}
                      className="p-1 disabled:opacity-30 hover:text-blue-400 text-slate-300"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="text-[11px] font-mono px-2 text-slate-300 font-bold">
                      {currentPage} / {totalPages}
                    </span>
                    <button
                      disabled={currentPage >= totalPages}
                      onClick={() => setCurrentPage((p) => p + 1)}
                      className="p-1 disabled:opacity-30 hover:text-blue-400 text-slate-300"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                )}

                {onPrintPdf && (
                  <button
                    onClick={onPrintPdf}
                    className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-bold shadow transition flex items-center gap-1.5"
                  >
                    <FileText className="w-4 h-4" />
                    Download PDF
                  </button>
                )}

                {onPrintDocx && (
                  <button
                    onClick={onPrintDocx}
                    className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-bold shadow transition flex items-center gap-1.5"
                  >
                    <FileSpreadsheet className="w-4 h-4" />
                    Download Word
                  </button>
                )}

                <button
                  onClick={() => setShowFullPreviewModal(false)}
                  className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded-lg transition ml-2"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="flex-1 bg-slate-950 p-6 overflow-auto flex items-center justify-center">
              {previewTab === 'GRID' && (
                <div
                  id="printable-sheet-container"
                  className="bg-white rounded-sm shadow-2xl p-6 transition-transform origin-center"
                  style={{
                    width: isLandscape ? '1080px' : '760px',
                    minHeight: isLandscape ? '760px' : '1080px',
                    transform: `scale(${zoomLevel})`,
                    transformOrigin: 'top center',
                  }}
                >
                  {/* Physical Sheet Label Grid */}
                  <div
                    className="w-full h-full grid gap-3"
                    style={{
                      gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
                      gridTemplateRows: `repeat(${rows}, minmax(0, 1fr))`,
                    }}
                  >
                    {Array.from({ length: labelsPerPage }).map((_, idx) => {
                      const ast = pageAssets[idx];
                      return ast ? (
                        <div key={ast.id || idx} className="flex items-center justify-center p-1 border border-dashed border-slate-200">
                          <AssetTagPreview
                            companyName={ast.company_name || 'TATA'}
                            logoUrl={ast.company_logo_path}
                            assetId={ast.asset_id}
                            sapNumber={ast.sap_number}
                            description={ast.description}
                            location={ast.location}
                            codeType={ast.code_type}
                            widthMm={labelWidthMm}
                            heightMm={labelHeightMm}
                            showActions={false}
                            scale={0.88}
                          />
                        </div>
                      ) : (
                        <div
                          key={idx}
                          className="border border-dashed border-slate-200 rounded flex items-center justify-center p-2 text-slate-300 text-xs font-mono"
                        >
                          [ Blank Slot ]
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {previewTab === 'PDF' && (
                <div className="w-full h-full flex flex-col items-center justify-center">
                  {loadingPdf ? (
                    <div className="text-white text-sm flex items-center gap-2">
                      <div className="w-5 h-5 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
                      Rendering Live PDF Sheet...
                    </div>
                  ) : pdfBlobUrl ? (
                    <iframe
                      src={pdfBlobUrl}
                      title="Sheet PDF Preview"
                      className="w-full h-full rounded-xl border border-slate-800 shadow-2xl bg-white"
                    />
                  ) : (
                    <div className="text-slate-400 text-xs">
                      Click below to generate and preview the PDF sheet.
                      <button
                        onClick={loadPdfStream}
                        className="mt-3 px-3 py-1.5 bg-red-600 text-white rounded font-bold block mx-auto"
                      >
                        Load Live PDF
                      </button>
                    </div>
                  )}
                </div>
              )}

              {previewTab === 'DOCX' && (
                <div className="max-w-3xl w-full bg-white rounded-xl p-8 shadow-2xl text-slate-900 space-y-6">
                  <div className="flex items-center justify-between pb-4 border-b border-slate-200">
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 bg-blue-100 text-blue-700 rounded-lg">
                        <FileSpreadsheet className="w-6 h-6" />
                      </div>
                      <div>
                        <h4 className="font-bold text-base text-slate-900">Microsoft Word (.docx) Sheet Preview</h4>
                        <p className="text-xs text-slate-500">
                          {pageSize} Layout • Table Matrix: {columns} columns × {rows} rows • Standard Word Processing Grid
                        </p>
                      </div>
                    </div>
                    {onPrintDocx && (
                      <button
                        onClick={onPrintDocx}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-2"
                      >
                        <Download className="w-4 h-4" />
                        Download Word (.docx)
                      </button>
                    )}
                  </div>

                  {/* Word document table simulation */}
                  <div className="border border-slate-300 rounded-lg p-4 bg-slate-50">
                    <div className="text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-2">
                      Document Page Setup Preview ({pageSize})
                    </div>
                    <table className="w-full border-collapse border border-slate-400 text-xs bg-white">
                      <tbody>
                        {Array.from({ length: Math.min(rows, 4) }).map((_, rIdx) => (
                          <tr key={rIdx} className="border-b border-slate-300">
                            {Array.from({ length: columns }).map((_, cIdx) => {
                              const astIdx = rIdx * columns + cIdx;
                              const ast = pageAssets[astIdx];
                              return (
                                <td key={cIdx} className="border border-slate-300 p-2 text-center align-middle">
                                  <div className="font-bold text-[10px] text-slate-900 uppercase">
                                    {ast?.company_name || 'TATA'}
                                  </div>
                                  <div className="text-[9px] text-slate-600 font-mono mt-0.5">
                                    SAP: {ast?.sap_number || '-'} | LOC: {ast?.location || '-'}
                                  </div>
                                  <div className="my-1 py-1 bg-slate-100 rounded text-[9px] font-mono font-bold text-slate-800">
                                    [ Barcode / QR Embedded ]
                                  </div>
                                  <div className="font-bold font-mono text-[10px] text-slate-900">
                                    {ast?.asset_id || 'ID-000000'}
                                  </div>
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {rows > 4 && (
                      <div className="text-center text-[10px] text-slate-500 mt-2 italic">
                        + {rows - 4} more rows per page formatted into Microsoft Word table cells
                      </div>
                    )}
                  </div>

                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-900 space-y-1">
                    <div className="font-bold">Word Document Features:</div>
                    <ul className="list-disc list-inside space-y-0.5 text-blue-800 text-[11px]">
                      <li>Native editable table cells with exact mm margins for printing on standard label stationery</li>
                      <li>High-resolution embedded Barcode (Code 128) and QR Code raster graphics</li>
                      <li>Fully editable in Microsoft Word, LibreOffice Writer, Google Docs, and WPS Office</li>
                    </ul>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
