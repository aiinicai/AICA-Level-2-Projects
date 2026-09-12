import React, { useState, useEffect } from 'react';
import {
  Printer,
  FileText,
  Grid,
  Sliders,
  CheckCircle2,
  HardDrive,
  Download,
  RefreshCw,
  Layers,
  FileSpreadsheet,
  Eye
} from 'lucide-react';
import api from '../services/api';
import { LabelSize, PrinterInfo, Asset } from '../types';
import { SheetLayoutVisualizer } from '../components/SheetLayoutVisualizer';
import { AssetTagPreview } from '../components/AssetTagPreview';

export const PrintingPage: React.FC = () => {
  const [activeMode, setActiveMode] = useState<'SHEET' | 'LABEL_PRINTER'>('SHEET');

  // Sheet layout configurations
  const [pageSize, setPageSize] = useState('A4');
  const [orientation, setOrientation] = useState<'PORTRAIT' | 'LANDSCAPE'>('PORTRAIT');
  const [labelWidth, setLabelWidth] = useState(70);
  const [labelHeight, setLabelHeight] = useState(35);
  const [marginTop, setMarginTop] = useState(10);
  const [marginBottom, setMarginBottom] = useState(10);
  const [marginLeft, setMarginLeft] = useState(10);
  const [marginRight, setMarginRight] = useState(10);
  const [horizontalGap, setHorizontalGap] = useState(3);
  const [verticalGap, setVerticalGap] = useState(3);

  // Layout calculation
  const [sheetCalc, setSheetCalc] = useState<{
    columns: number;
    rows: number;
    labels_per_page: number;
    estimated_pages: number;
  }>({
    columns: 2,
    rows: 7,
    labels_per_page: 14,
    estimated_pages: 1,
  });

  // Available assets
  const [availableAssets, setAvailableAssets] = useState<Asset[]>([]);
  const [selectedAssetIds, setSelectedAssetIds] = useState<number[]>([]);

  // Hardware & Label Printer configurations
  const [printers, setPrinters] = useState<PrinterInfo[]>([]);
  const [selectedPrinter, setSelectedPrinter] = useState<string>('');
  const [labelSizes, setLabelSizes] = useState<LabelSize[]>([]);
  const [selectedSizeId, setSelectedSizeId] = useState<number | null>(null);
  const [copies, setCopies] = useState(1);
  const [isPrinting, setIsPrinting] = useState(false);
  const [printSuccessMsg, setPrintSuccessMsg] = useState('');

  // Fetch initial assets, printers & label sizes
  const loadInitialData = async () => {
    try {
      const [resAssets, resPrinters, resSizes] = await Promise.all([
        api.get<Asset[]>('/assets?limit=50'),
        api.get<PrinterInfo[]>('/printing/printers'),
        api.get<LabelSize[]>('/printing/label-sizes'),
      ]);
      setAvailableAssets(resAssets.data);
      setSelectedAssetIds(resAssets.data.map((a) => a.id));

      setPrinters(resPrinters.data);
      if (resPrinters.data.length > 0) {
        const def = resPrinters.data.find((p) => p.is_default) || resPrinters.data[0];
        setSelectedPrinter(def.name);
      }

      setLabelSizes(resSizes.data);
      if (resSizes.data.length > 0) {
        setSelectedSizeId(resSizes.data[0].id);
      }
    } catch (e) {
      console.error('Failed to load printing config:', e);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  // Recalculate sheet layout
  useEffect(() => {
    const calc = async () => {
      try {
        const res = await api.post(
          '/printing/calculate-sheet',
          {
            page_size: pageSize,
            orientation: orientation,
            label_width_mm: labelWidth,
            label_height_mm: labelHeight,
            margin_top_mm: marginTop,
            margin_bottom_mm: marginBottom,
            margin_left_mm: marginLeft,
            margin_right_mm: marginRight,
            horizontal_gap_mm: horizontalGap,
            vertical_gap_mm: verticalGap,
          },
          {
            params: { item_count: selectedAssetIds.length || 1 },
          }
        );
        setSheetCalc({
          columns: res.data.columns,
          rows: res.data.rows,
          labels_per_page: res.data.labels_per_page,
          estimated_pages: res.data.estimated_pages,
        });
      } catch (e) {
        console.error('Calculation error:', e);
      }
    };
    calc();
  }, [pageSize, orientation, labelWidth, labelHeight, marginTop, marginBottom, marginLeft, marginRight, horizontalGap, verticalGap, selectedAssetIds.length]);

  const applyPresetMatrix = (cols: number, rows: number, w: number, h: number) => {
    setLabelWidth(w);
    setLabelHeight(h);
    setSheetCalc((prev) => ({
      ...prev,
      columns: cols,
      rows: rows,
      labels_per_page: cols * rows,
    }));
  };

  const handleDownloadSheetPdf = () => {
    if (selectedAssetIds.length === 0) {
      alert('Please select at least one asset to print.');
      return;
    }

    const payload = {
      config: {
        page_size: pageSize,
        orientation: orientation,
        label_width_mm: labelWidth,
        label_height_mm: labelHeight,
        margin_top_mm: marginTop,
        margin_bottom_mm: marginBottom,
        margin_left_mm: marginLeft,
        margin_right_mm: marginRight,
        horizontal_gap_mm: horizontalGap,
        vertical_gap_mm: verticalGap,
        columns: sheetCalc.columns,
        rows: sheetCalc.rows,
      },
      asset_ids: selectedAssetIds,
    };

    api
      .post('/printing/generate-sheet-pdf', payload.config, {
        params: { asset_ids: selectedAssetIds },
        responseType: 'blob',
      })
      .then((response) => {
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `Asset_Tags_${pageSize}_Sheet.pdf`);
        document.body.appendChild(link);
        link.click();
        link.remove();
      });
  };

  const handleDownloadSheetDocx = () => {
    if (selectedAssetIds.length === 0) {
      alert('Please select at least one asset to print.');
      return;
    }

    const payload = {
      config: {
        page_size: pageSize,
        orientation: orientation,
        label_width_mm: labelWidth,
        label_height_mm: labelHeight,
        margin_top_mm: marginTop,
        margin_bottom_mm: marginBottom,
        margin_left_mm: marginLeft,
        margin_right_mm: marginRight,
        horizontal_gap_mm: horizontalGap,
        vertical_gap_mm: verticalGap,
        columns: sheetCalc.columns,
        rows: sheetCalc.rows,
      },
      asset_ids: selectedAssetIds,
    };

    api
      .post('/printing/generate-sheet-docx', payload.config, {
        params: { asset_ids: selectedAssetIds },
        responseType: 'blob',
      })
      .then((response) => {
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `Asset_Tags_Sheet.docx`);
        document.body.appendChild(link);
        link.click();
        link.remove();
      });
  };

  const handleSendToLabelPrinter = async () => {
    if (!selectedPrinter) {
      alert('Please select a target label printer.');
      return;
    }
    if (selectedAssetIds.length === 0) {
      alert('Please select at least one asset.');
      return;
    }

    setIsPrinting(true);
    setPrintSuccessMsg('');

    try {
      const res = await api.post('/printing/direct-print', {
        printer_name: selectedPrinter,
        asset_ids: selectedAssetIds,
        label_size_id: selectedSizeId,
        copies: copies,
      });
      setPrintSuccessMsg(
        `Successfully sent ${res.data.assets_count} label(s) to ${res.data.printer}!`
      );
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Direct printing job failed.');
    } finally {
      setIsPrinting(false);
    }
  };

  const selectedAssetsList = availableAssets.filter((a) => selectedAssetIds.includes(a.id));
  const activeLabelSize = labelSizes.find((s) => s.id === selectedSizeId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Sheet & Label Printer Hub</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Precision layout engine for A4/A3 sheet printing and direct thermal roll printers (Zebra, Brother, DYMO, TSC)
          </p>
        </div>

        {/* Mode Switcher */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
          <button
            onClick={() => setActiveMode('SHEET')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition ${
              activeMode === 'SHEET'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Grid className="w-4 h-4 text-blue-600" />
            A4 / A3 Sheet Printing
          </button>
          <button
            onClick={() => setActiveMode('LABEL_PRINTER')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition ${
              activeMode === 'LABEL_PRINTER'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Printer className="w-4 h-4 text-indigo-600" />
            Direct Label Printer
          </button>
        </div>
      </div>

      {printSuccessMsg && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs p-4 rounded-xl flex items-center gap-2 font-semibold">
          <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          {printSuccessMsg}
        </div>
      )}

      {/* Main Mode 1: A4 / A3 Sheet Printing */}
      {activeMode === 'SHEET' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Settings (6 Cols) */}
          <div className="lg:col-span-6 bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-5">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider pb-3 border-b border-slate-100">
              Sheet Dimensions & Quick Presets
            </h2>

            {/* Quick Presets for Sheet Matrix */}
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1.5">
                Quick Labels per Sheet Presets
              </label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => applyPresetMatrix(2, 7, 70, 35)}
                  className="p-2 bg-slate-50 border border-slate-200 hover:border-blue-500 rounded-lg text-left transition"
                >
                  <div className="text-xs font-bold text-slate-900">14 Labels / Page</div>
                  <div className="text-[10px] text-slate-500">2 cols × 7 rows (70×35mm)</div>
                </button>
                <button
                  type="button"
                  onClick={() => applyPresetMatrix(3, 7, 60, 35)}
                  className="p-2 bg-slate-50 border border-slate-200 hover:border-blue-500 rounded-lg text-left transition"
                >
                  <div className="text-xs font-bold text-slate-900">21 Labels / Page</div>
                  <div className="text-[10px] text-slate-500">3 cols × 7 rows (60×35mm)</div>
                </button>
                <button
                  type="button"
                  onClick={() => applyPresetMatrix(3, 8, 60, 30)}
                  className="p-2 bg-slate-50 border border-slate-200 hover:border-blue-500 rounded-lg text-left transition"
                >
                  <div className="text-xs font-bold text-slate-900">24 Labels / Page</div>
                  <div className="text-[10px] text-slate-500">3 cols × 8 rows (60×30mm)</div>
                </button>
                <button
                  type="button"
                  onClick={() => applyPresetMatrix(2, 6, 80, 40)}
                  className="p-2 bg-slate-50 border border-slate-200 hover:border-blue-500 rounded-lg text-left transition"
                >
                  <div className="text-xs font-bold text-slate-900">12 Labels / Page</div>
                  <div className="text-[10px] text-slate-500">2 cols × 6 rows (80×40mm)</div>
                </button>
                <button
                  type="button"
                  onClick={() => applyPresetMatrix(2, 3, 90, 80)}
                  className="p-2 bg-slate-50 border border-slate-200 hover:border-blue-500 rounded-lg text-left transition"
                >
                  <div className="text-xs font-bold text-slate-900">6 Labels / Page</div>
                  <div className="text-[10px] text-slate-500">2 cols × 3 rows (Large)</div>
                </button>
                <button
                  type="button"
                  onClick={() => applyPresetMatrix(3, 10, 50, 25)}
                  className="p-2 bg-slate-50 border border-slate-200 hover:border-blue-500 rounded-lg text-left transition"
                >
                  <div className="text-xs font-bold text-slate-900">30 Labels / Page</div>
                  <div className="text-[10px] text-slate-500">3 cols × 10 rows (50×25mm)</div>
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Paper Standard</label>
                <select
                  value={pageSize}
                  onChange={(e) => setPageSize(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 font-medium"
                >
                  <option value="A4">A4 (210 × 297 mm)</option>
                  <option value="A3">A3 (297 × 420 mm)</option>
                  <option value="LETTER">Letter (216 × 279 mm)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Sheet Orientation</label>
                <select
                  value={orientation}
                  onChange={(e) => setOrientation(e.target.value as any)}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 font-medium"
                >
                  <option value="PORTRAIT">Portrait</option>
                  <option value="LANDSCAPE">Landscape</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Label Width (mm)</label>
                <input
                  type="number"
                  value={labelWidth}
                  onChange={(e) => setLabelWidth(Number(e.target.value))}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 font-mono font-bold"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Label Height (mm)</label>
                <input
                  type="number"
                  value={labelHeight}
                  onChange={(e) => setLabelHeight(Number(e.target.value))}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 font-mono font-bold"
                />
              </div>
            </div>

            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
              <div className="text-xs font-bold text-slate-800">Margins & Spacing (mm)</div>
              <div className="grid grid-cols-4 gap-2 text-xs">
                <div>
                  <span className="text-[10px] text-slate-500">Top</span>
                  <input
                    type="number"
                    value={marginTop}
                    onChange={(e) => setMarginTop(Number(e.target.value))}
                    className="w-full text-xs bg-white border border-slate-300 rounded p-1.5 font-mono"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-slate-500">Bottom</span>
                  <input
                    type="number"
                    value={marginBottom}
                    onChange={(e) => setMarginBottom(Number(e.target.value))}
                    className="w-full text-xs bg-white border border-slate-300 rounded p-1.5 font-mono"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-slate-500">Left</span>
                  <input
                    type="number"
                    value={marginLeft}
                    onChange={(e) => setMarginLeft(Number(e.target.value))}
                    className="w-full text-xs bg-white border border-slate-300 rounded p-1.5 font-mono"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-slate-500">Right</span>
                  <input
                    type="number"
                    value={marginRight}
                    onChange={(e) => setMarginRight(Number(e.target.value))}
                    className="w-full text-xs bg-white border border-slate-300 rounded p-1.5 font-mono"
                  />
                </div>
              </div>
            </div>

            {/* Output Download Actions */}
            <div className="grid grid-cols-2 gap-3 pt-2">
              <button
                type="button"
                onClick={handleDownloadSheetPdf}
                className="py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl shadow-lg shadow-blue-600/30 transition flex items-center justify-center gap-2"
              >
                <FileText className="w-4 h-4" />
                <span>Download PDF Sheet</span>
              </button>

              <button
                type="button"
                onClick={handleDownloadSheetDocx}
                className="py-3 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl shadow-lg transition flex items-center justify-center gap-2"
              >
                <FileSpreadsheet className="w-4 h-4 text-blue-400" />
                <span>Download Word (.docx)</span>
              </button>
            </div>
          </div>

          {/* Right Visualizer & Preview (6 Cols) */}
          <div className="lg:col-span-6 space-y-4">
            <SheetLayoutVisualizer
              pageSize={pageSize}
              orientation={orientation}
              columns={sheetCalc.columns}
              rows={sheetCalc.rows}
              labelsPerPage={sheetCalc.labels_per_page}
              totalItems={selectedAssetIds.length}
              labelWidthMm={labelWidth}
              labelHeightMm={labelHeight}
              assets={selectedAssetsList}
              onPrintPdf={handleDownloadSheetPdf}
              onPrintDocx={handleDownloadSheetDocx}
            />
          </div>
        </div>
      )}

      {/* Main Mode 2: Direct Thermal Label Printer */}
      {activeMode === 'LABEL_PRINTER' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Hardware Config (6 Cols) */}
          <div className="lg:col-span-6 bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-5">
            <h2 className="text-sm font-bold text-slate-900 pb-3 border-b border-slate-100 flex items-center gap-2">
              <HardDrive className="w-5 h-5 text-indigo-600" />
              Windows Thermal Label Spooler
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1.5">
                  Target Physical Printer
                </label>
                <select
                  value={selectedPrinter}
                  onChange={(e) => setSelectedPrinter(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 font-medium"
                >
                  {printers.map((p, idx) => (
                    <option key={idx} value={p.name}>
                      {p.name} {p.is_default ? '(Default)' : ''} — [{p.driver_name}]
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1.5">
                  Label Media Preset (Roll / Continuous)
                </label>
                <select
                  value={selectedSizeId || ''}
                  onChange={(e) => setSelectedSizeId(Number(e.target.value))}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 font-medium"
                >
                  {labelSizes.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} — {s.width_mm} × {s.height_mm} mm ({s.category})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Copies per Asset</label>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={copies}
                    onChange={(e) => setCopies(Number(e.target.value))}
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 font-mono font-bold"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Assets Queued</label>
                  <div className="text-xs bg-slate-100 border border-slate-200 rounded-lg p-2 font-mono font-bold text-slate-800">
                    {selectedAssetIds.length} Assets Selected
                  </div>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={handleSendToLabelPrinter}
              disabled={isPrinting}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-lg shadow-indigo-600/30 transition flex items-center justify-center gap-2"
            >
              {isPrinting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Spooling to Physical Printer...</span>
                </>
              ) : (
                <>
                  <Printer className="w-4 h-4" />
                  <span>Send Direct Print Job ({selectedAssetIds.length * copies} Labels)</span>
                </>
              )}
            </button>
          </div>

          {/* Roll Live Preview (6 Cols) */}
          <div className="lg:col-span-6 bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col items-center justify-center">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider pb-3 mb-4 border-b border-slate-100 w-full text-center">
              Direct Thermal Roll Preview
            </h3>

            <div className="p-6 bg-slate-50 rounded-xl border border-slate-200 flex justify-center w-full">
              <AssetTagPreview
                companyName={selectedAssetsList[0]?.company_name || 'TATA'}
                logoUrl={selectedAssetsList[0]?.company_logo_path}
                assetId={selectedAssetsList[0]?.asset_id || 'TATA-000001'}
                sapNumber={selectedAssetsList[0]?.sap_number || '41009821-0'}
                description={selectedAssetsList[0]?.description || 'SERVER DELL POWEREDGE R750'}
                location={selectedAssetsList[0]?.location || 'MUM-DC-BAY-12'}
                codeType={selectedAssetsList[0]?.code_type || 'BARCODE'}
                widthMm={activeLabelSize?.width_mm || 70}
                heightMm={activeLabelSize?.height_mm || 35}
                showActions={true}
                scale={1.1}
                id={selectedAssetsList[0]?.id}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
